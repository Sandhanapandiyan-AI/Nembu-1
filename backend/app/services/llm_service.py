import requests
import json
import logging
import re
from typing import List, Dict, Optional, Tuple, Any
from sqlalchemy import text
from .db_service import DatabaseService
from .insert_handler import InsertQueryHandler

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.ollama_url = "http://localhost:11434/api/generate"
        self.model = "SqlGenerator"
        self.db_service = DatabaseService()
        self.insert_handler = InsertQueryHandler()
        logger.info(f" Initialized LLM Service with model: {self.model}")
        self.last_query_context = None
        self.pending_insert_query = None

        # Fetch database schema
        self.db_schema = self.db_service.get_database_schema()

        # Print a message that the schema is loaded
        print("\n" + "="*80)
        print("DATABASE SCHEMA LOADED FOR CONTEXT")
        print("="*80)

        logger.info(" Loaded database schema for context")
          # Update system prompt with schema
        self.system_prompt = f"""
Database schema:

{self.db_schema}

Instructions:
1. Generate only SQL query
2. Query must be wrapped in ```sql ``` tags
3. No explanations or other text
4. When querying employee data, include department names when possible
5. For INSERT queries:
   - Use '?' as placeholder for values that should be collected from the user
   - For employee_identifier, use a placeholder '?' as it's auto-generated
   - For date fields like employee_hire_date, use '?' to prompt for user input
   - ALWAYS use '?' for department_identifier in employee table (user will provide department name)
   - NEVER provide actual department_identifier values, always use '?' for these fields"""

    def _extract_sql_and_explanation(self, response: str) -> Tuple[str, str]:
        """Extract SQL query and explanation from the response."""
        lines = response.split('\n')
        sql_query = ""
        explanation = []
        in_code_block = False

        for line in lines:
            if '```' in line:
                in_code_block = not in_code_block
                continue

            if in_code_block:
                sql_query += line + "\n"
            else:
                explanation.append(line)

        return sql_query.strip(), "\n".join(explanation).strip()

    def format_response(self, response: str, query_results: Optional[Dict] = None) -> Dict[str, Any]:
        """Format the response with SQL query and results as JSON."""
        logger.info(" Formatting LLM response as JSON")
        sql_query, explanation = self._extract_sql_and_explanation(response)

        result = {
            "sql_query": sql_query,
            "explanation": explanation
        }

        # Add query results if available
        if query_results:
            result.update(self.db_service.get_results_as_json(query_results))
        else:
            result.update({
                "success": False,
                "message": "No query results available",
                "data": None
            })

        return result

    def _get_available_departments(self) -> List[str]:
        """Get a list of available department names from the database."""
        try:
            # Query the database for department names
            departments = []
            with self.db_service.engine.connect() as connection:
                query = "SELECT department_name FROM department ORDER BY department_name"
                result = connection.execute(text(query))
                departments = [row[0] for row in result]

            return departments
        except Exception as e:
            logger.error(f"Error getting department list: {str(e)}")
            return []

    def is_follow_up_question(self, message: str) -> bool:
        """Check if the message is a follow-up question about the last query."""
        follow_up_triggers = [
            "explain", "clarify", "what does this mean",
            "i don't understand", "can you explain",
            "what do you mean", "didn't understand",
            "how does this work", "tell me more"
        ]
        message = message.lower().strip()
        return any(trigger in message for trigger in follow_up_triggers) and self.last_query_context is not None

    def is_insert_value_input(self, _: str) -> bool:
        """Check if the message is providing a value for a pending INSERT query."""
        return self.pending_insert_query is not None

    def process_insert_value_input(self, user_message: str) -> Dict[str, Any]:
        """Process user input for a pending INSERT query with missing values."""
        if not self.pending_insert_query:
            return {
                "success": False,
                "error": "No pending INSERT query to process",
                "data": None
            }

        # Get the current field being requested
        current_field = self.pending_insert_query.get("current_field")
        if not current_field:
            return {
                "success": False,
                "error": "No field is currently being requested",
                "data": None
            }

        # Add the user input to the collected values
        field_name = current_field["name"]
        self.pending_insert_query["collected_values"][field_name] = user_message

        # Update the list of fields that still need values
        remaining_fields = []
        for field in self.pending_insert_query.get("remaining_fields", []):
            if field["name"] != field_name:
                remaining_fields.append(field)

        # Check if we have more fields to collect
        if remaining_fields:
            # Update the pending query with the next field
            self.pending_insert_query["remaining_fields"] = remaining_fields
            self.pending_insert_query["current_field"] = remaining_fields[0]

            # Return a response asking for the next field
            next_field = remaining_fields[0]

            # Check if this is a foreign key field with a display name
            field_message = ""
            if next_field.get("is_foreign_key") and next_field.get("display_name") == "department_name":
                # For department foreign keys, ask for the department name
                field_message = f"Please provide the department name"

                # Get available departments for the user to choose from
                departments = self._get_available_departments()
                if departments:
                    field_message += f". Available departments: {', '.join(departments)}"
            else:
                # Regular field
                field_message = f"Please provide a value for '{next_field['name']}' ({next_field['description']})"

            return {
                "success": True,
                "query_type": "INSERT_FIELD_REQUEST",
                "message": field_message,
                "field": next_field,
                "data": None
            }
        else:
            # All fields collected, generate the complete query
            analysis = self.pending_insert_query["analysis"]
            collected_values = self.pending_insert_query["collected_values"]

            # Generate the complete INSERT query
            complete_query = self.insert_handler.generate_complete_query(analysis, collected_values)

            # Reset the pending query
            self.pending_insert_query = None

            # Generate a new response with the complete query
            return self.generate_sql_response(complete_query, f"INSERT query completed with all required values.")

    def generate_sql_response(self, sql_query: str, explanation: str = "") -> Dict[str, Any]:
        """Generate a response for a SQL query."""
        try:
            # Execute the SQL query
            query_results = self.db_service.execute_query(sql_query)

            # Format the response
            raw_response = f"{explanation}\n\n```sql\n{sql_query}\n```"
            formatted_response = self.format_response(raw_response, query_results)

            # Store context for follow-up questions
            self.last_query_context = formatted_response

            return formatted_response

        except Exception as e:
            logger.error(f" Error executing SQL query: {str(e)}")
            return {
                "success": False,
                "error": f"Error executing SQL query: {str(e)}",
                "sql_query": sql_query,
                "explanation": explanation,
                "data": None
            }

    def generate_response(self, user_message: str) -> Dict[str, Any]:
        """Generate a response including SQL execution and results as JSON."""
        logger.info(" Starting SQL generation process")

        try:
            # Check if this is input for a pending INSERT query
            if self.is_insert_value_input(user_message):
                logger.info("🔄 Processing input for pending INSERT query")
                return self.process_insert_value_input(user_message)

            # Check if this is a follow-up question
            if self.is_follow_up_question(user_message) and self.last_query_context:
                logger.info("🔄 Returning previous query results")
                return self.last_query_context

            # Prepare request for new query
            prompt = f"{self.system_prompt}\n\nUser: {user_message}\n\nAssistant:"
            request_data = {
                "model": self.model,
                "prompt": prompt,
                "stream": False
            }

            logger.info(f" Sending request ({len(user_message)} chars)")

            # Make request to Ollama
            response = requests.post(self.ollama_url, json=request_data)
            response.raise_for_status()

            # Parse response
            result = response.json()
            raw_response = result.get('response', '')

            # Extract SQL and explanation
            sql_query, explanation = self._extract_sql_and_explanation(raw_response)

            # Check if this is an INSERT query that might need additional values
            if sql_query.strip().upper().startswith("INSERT"):
                # Analyze the INSERT query
                analysis = self.insert_handler.analyze_insert_query(sql_query)

                # Force interactive mode for certain user queries
                force_interactive = False
                if any(phrase in user_message.lower() for phrase in ["add new", "create new", "insert new"]):
                    logger.info(f" Forcing interactive mode for INSERT query based on user message: '{user_message}'")
                    force_interactive = True

                # Check if the query has placeholders
                has_placeholders = "?" in sql_query
                if has_placeholders:
                    logger.info(f"🔍 INSERT query contains placeholders, will collect values interactively")
                    force_interactive = True

                # If the query needs user input or we're forcing interactive mode
                if (analysis.get("is_valid", False) and (analysis.get("needs_input", False) or force_interactive)):
                    # Get all fields from the table schema that aren't auto-increment
                    table_name = analysis.get("table_name")
                    table_schema = self.insert_handler._get_table_schema(table_name)

                    # Determine which fields to collect
                    if force_interactive:
                        # For forced interactive mode, collect all non-auto-increment fields
                        # that aren't already provided with valid values
                        missing_fields = []
                        columns = analysis.get("columns", [])
                        values = analysis.get("values", [])

                        # First, add any explicitly missing fields from the analysis
                        missing_fields.extend(analysis.get("missing_required", []))
                        missing_fields.extend(analysis.get("missing_values", []))

                        # Then, check for fields with placeholders
                        for i, col in enumerate(columns):
                            if i < len(values) and values[i] == "?":
                                # Check if this field is already in missing_fields
                                if not any(field["name"] == col for field in missing_fields):
                                    col_info = table_schema.get(col, {})
                                    # Skip auto-increment fields
                                    if not col_info.get("is_autoincrement", False):
                                        # Check if it's a foreign key
                                        is_foreign_key = col_info.get("is_foreign_key", False)
                                        fk_info = col_info.get("foreign_key_info")

                                        if is_foreign_key and fk_info and fk_info["referred_table"] == "department" and fk_info["referred_columns"][0] == "department_identifier":
                                            # Special handling for department references
                                            logger.info(f"Column {col} is a foreign key to department table, will ask for department name")

                                            # Add a special field for department name
                                            missing_fields.append({
                                                "name": col,
                                                "type": str(col_info.get("type", "unknown")),
                                                "description": "Department name",
                                                "is_foreign_key": True,
                                                "display_name": "department_name",
                                                "referred_table": fk_info["referred_table"],
                                                "referred_column": fk_info["referred_columns"][0]
                                            })
                                        else:
                                            # Regular field
                                            missing_fields.append({
                                                "name": col,
                                                "type": str(col_info.get("type", "unknown")),
                                                "description": f"Field for {table_name}"
                                            })

                        # If we still don't have any fields to collect, add all non-auto-increment fields
                        if not missing_fields and table_schema:
                            for col_name, col_info in table_schema.items():
                                # Skip auto-increment fields
                                if col_info.get("is_autoincrement", False):
                                    continue
                                # Skip fields that already have valid values
                                if col_name in columns:
                                    idx = columns.index(col_name)
                                    if idx < len(values) and values[idx] != "?" and values[idx].upper() != "NULL":
                                        continue
                                # Check if it's a foreign key
                                is_foreign_key = col_info.get("is_foreign_key", False)
                                fk_info = col_info.get("foreign_key_info")

                                if is_foreign_key and fk_info and fk_info["referred_table"] == "department" and fk_info["referred_columns"][0] == "department_identifier":
                                    # Special handling for department references
                                    logger.info(f"Column {col_name} is a foreign key to department table, will ask for department name")

                                    # Add a special field for department name
                                    missing_fields.append({
                                        "name": col_name,
                                        "type": str(col_info.get("type", "unknown")),
                                        "description": "Department name",
                                        "is_foreign_key": True,
                                        "display_name": "department_name",
                                        "referred_table": fk_info["referred_table"],
                                        "referred_column": fk_info["referred_columns"][0]
                                    })
                                else:
                                    # Regular field
                                    missing_fields.append({
                                        "name": col_name,
                                        "type": str(col_info.get("type", "unknown")),
                                        "description": f"Field for {table_name}"
                                    })
                    else:
                        # For normal mode, use the fields identified in the analysis
                        missing_fields = analysis.get("missing_required", []) + analysis.get("missing_values", [])

                    if missing_fields:
                        logger.info(f" INSERT query needs additional values for {len(missing_fields)} fields")

                        # Set up the pending query
                        self.pending_insert_query = {
                            "analysis": analysis,
                            "remaining_fields": missing_fields[1:],  # All fields except the first
                            "current_field": missing_fields[0],      # First field to request
                            "collected_values": {},                  # Values collected so far
                            "original_query": sql_query              # Original query
                        }

                        # Return a response asking for the first missing value
                        first_field = missing_fields[0]

                        # Check if this is a foreign key field with a display name
                        field_message = ""
                        if first_field.get("is_foreign_key") and first_field.get("display_name") == "department_name":
                            # For department foreign keys, ask for the department name
                            field_message = f"Please provide the department name"

                            # Get available departments for the user to choose from
                            departments = self._get_available_departments()
                            if departments:
                                field_message += f". Available departments: {', '.join(departments)}"
                        else:
                            # Regular field
                            field_message = f"Please provide a value for '{first_field['name']}' ({first_field['description']})"

                        return {
                            "success": True,
                            "query_type": "INSERT_FIELD_REQUEST",
                            "message": field_message,
                            "field": first_field,
                            "data": None
                        }

            # For non-INSERT queries or INSERT queries that don't need input
            return self.generate_sql_response(sql_query, explanation)

        except requests.exceptions.RequestException as e:
            logger.error(f" Error communicating: {str(e)}")
            return {
                "success": False,
                "error": f"Error communicating : {str(e)}",
                "sql_query": "",
                "explanation": "",
                "data": None
            }
        except Exception as e:
            logger.error(f" Unexpected error: {str(e)}")
            return {
                "success": False,
                "error": f"Unexpected error in LLM service: {str(e)}",
                "sql_query": "",
                "explanation": "",
                "data": None
            }
