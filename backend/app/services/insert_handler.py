import re
import logging
from typing import Dict, List, Tuple, Optional, Any
from sqlalchemy import create_engine, text, inspect
from .config import DATABASE_URL

# Configure logging
logger = logging.getLogger(__name__)

class InsertQueryHandler:
    """
    Handler for INSERT queries that detects missing values and helps collect them
    from the user interactively.
    """

    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
        logger.info(" Initialized InsertQueryHandler")

        # Cache for table schemas
        self._table_schemas = {}

        # Cache for foreign key relationships
        self._foreign_keys = {}

        # Cache for reference data (e.g., department names to IDs)
        self._reference_data = {}

        # Print foreign key relationships for debugging
        self._print_foreign_key_relationships()

    def analyze_insert_query(self, query: str) -> Dict[str, Any]:
        """
        Analyze an INSERT query to detect missing values and required fields.

        Args:
            query: The SQL INSERT query to analyze

        Returns:
            Dict containing analysis results
        """
        try:
            logger.info(f"Analyzing INSERT query: {query}")

            # Extract table name and columns from the query
            table_name, columns, values = self._parse_insert_query(query)

            if not table_name:
                logger.warning("Could not determine target table for INSERT query")
                return {
                    "is_valid": False,
                    "error": "Could not determine target table for INSERT query",
                    "query": query
                }

            # Get table schema
            table_schema = self._get_table_schema(table_name)

            if not table_schema:
                logger.warning(f"Table '{table_name}' not found in database")
                return {
                    "is_valid": False,
                    "error": f"Table '{table_name}' not found in database",
                    "query": query
                }

            logger.info(f"Analyzing INSERT query for table: {table_name}")
            logger.info(f"Columns in query: {columns}")
            logger.info(f"Values in query: {values}")

            # Check for missing required columns
            missing_required = []
            for col_name, col_info in table_schema.items():
                # Skip auto-increment primary keys
                if col_info.get("is_autoincrement", False):
                    logger.info(f"Skipping auto-increment column: {col_name}")
                    continue

                # Check if required column is missing
                if not col_info.get("nullable", True) and col_name not in columns:
                    logger.info(f"Found missing required column: {col_name}")
                    missing_required.append({
                        "name": col_name,
                        "type": str(col_info.get("type", "unknown")),
                        "description": f"Required field for {table_name}"
                    })

            # Check for NULL or missing values in the provided columns
            missing_values = []
            for i, col in enumerate(columns):
                # Check if value is missing, NULL, or a placeholder
                if i >= len(values) or not values[i] or values[i].upper() == "NULL" or values[i] == "?" or values[i] == "''":
                    col_info = table_schema.get(col, {})

                    # Skip if it's a nullable column with NULL value
                    if values[i] and values[i].upper() == "NULL" and col_info.get("nullable", True):
                        logger.info(f"Column {col} has NULL value but is nullable, not requesting input")
                        continue

                    # Skip if it's an auto-increment column
                    if col_info.get("is_autoincrement", False):
                        logger.info(f"Column {col} is auto-increment, not requesting input")
                        continue

                    # Check if it's a foreign key
                    if col_info.get("is_foreign_key", False) and col_info.get("foreign_key_info"):
                        fk_info = col_info["foreign_key_info"]
                        referred_table = fk_info["referred_table"]
                        referred_column = fk_info["referred_columns"][0] if fk_info["referred_columns"] else None

                        # Special handling for department references
                        if referred_table == "department" and referred_column == "department_identifier":
                            logger.info(f"Column {col} is a foreign key to department table, will ask for department name")

                            # Force this field to be collected, even if it has a value
                            # This ensures we always ask for department name
                            missing_values.append({
                                "name": col,
                                "type": str(col_info.get("type", "unknown")),
                                "description": f"Department name",
                                "is_foreign_key": True,
                                "display_name": "department_name",
                                "referred_table": referred_table,
                                "referred_column": referred_column
                            })
                            continue

                    # Regular field
                    logger.info(f"Found missing value for column: {col}")
                    missing_values.append({
                        "name": col,
                        "type": str(col_info.get("type", "unknown")),
                        "description": f"Field for {table_name}"
                    })

            # Determine if query needs user input
            needs_input = len(missing_required) > 0 or len(missing_values) > 0

            result = {
                "is_valid": True,
                "needs_input": needs_input,
                "table_name": table_name,
                "columns": columns,
                "values": values,
                "missing_required": missing_required,
                "missing_values": missing_values,
                "query": query
            }

            logger.info(f"Analysis result: needs_input={needs_input}, missing_required={len(missing_required)}, missing_values={len(missing_values)}")
            return result

        except Exception as e:
            logger.error(f"Error analyzing INSERT query: {str(e)}")
            return {
                "is_valid": False,
                "error": f"Error analyzing query: {str(e)}",
                "query": query
            }

    def _parse_insert_query(self, query: str) -> Tuple[Optional[str], List[str], List[str]]:
        """
        Parse an INSERT query to extract table name, columns, and values.

        Args:
            query: The SQL INSERT query to parse

        Returns:
            Tuple of (table_name, columns, values)
        """
        # Clean up the query - remove extra whitespace and newlines
        clean_query = ' '.join(query.strip().split())
        logger.info(f"Parsing INSERT query: {clean_query}")

        try:
            # Basic pattern for INSERT queries with column specification
            # INSERT INTO table_name (col1, col2, ...) VALUES (val1, val2, ...)
            pattern = r"INSERT\s+INTO\s+(\w+)(?:\s*\.\s*\w+)?\s*\(([^)]+)\)\s*VALUES\s*\(([^)]+)\)"
            match = re.search(pattern, clean_query, re.IGNORECASE)

            if match:
                table_name = match.group(1)
                columns = [col.strip() for col in match.group(2).split(',')]
                values = [val.strip() for val in match.group(3).split(',')]
                logger.info(f"Parsed INSERT query with columns: table={table_name}, columns={columns}, values={values}")
                return table_name, columns, values

            # Try alternative pattern without column specification
            # INSERT INTO table_name VALUES (val1, val2, ...)
            alt_pattern = r"INSERT\s+INTO\s+(\w+)(?:\s*\.\s*\w+)?\s+VALUES\s*\(([^)]+)\)"
            alt_match = re.search(alt_pattern, clean_query, re.IGNORECASE)

            if alt_match:
                table_name = alt_match.group(1)
                # Get all columns from the table schema
                table_schema = self._get_table_schema(table_name)
                if table_schema:
                    columns = list(table_schema.keys())
                    values = [val.strip() for val in alt_match.group(2).split(',')]
                    logger.info(f"Parsed INSERT query without columns: table={table_name}, inferred columns={columns}, values={values}")
                    return table_name, columns, values

            # If we get here, we couldn't parse the query
            logger.warning(f"Failed to parse INSERT query: {clean_query}")
            return None, [], []

        except Exception as e:
            logger.error(f"Error parsing INSERT query: {str(e)}")
            return None, [], []

    def _get_table_schema(self, table_name: str) -> Dict[str, Dict[str, Any]]:
        """
        Get the schema for a specific table.

        Args:
            table_name: Name of the table

        Returns:
            Dict mapping column names to their properties
        """
        # Check cache first
        if table_name in self._table_schemas:
            return self._table_schemas[table_name]

        try:
            inspector = inspect(self.engine)

            # Check if table exists
            if table_name not in inspector.get_table_names():
                return {}

            # Get columns
            columns = inspector.get_columns(table_name)
            primary_keys = inspector.get_pk_constraint(table_name)['constrained_columns']

            # Get foreign keys
            foreign_keys = inspector.get_foreign_keys(table_name)

            # Build schema dict
            schema = {}
            for col in columns:
                is_pk = col['name'] in primary_keys

                # Check if this column is a foreign key
                is_fk = False
                fk_info = None
                for fk in foreign_keys:
                    if col['name'] in fk['constrained_columns']:
                        is_fk = True
                        fk_info = {
                            "referred_table": fk['referred_table'],
                            "referred_columns": fk['referred_columns'],
                        }
                        break

                schema[col['name']] = {
                    "type": col['type'],
                    "nullable": col.get('nullable', True),
                    "default": col.get('default'),
                    "is_primary_key": is_pk,
                    "is_autoincrement": col.get('autoincrement', False) and is_pk,
                    "is_foreign_key": is_fk,
                    "foreign_key_info": fk_info
                }

            # Cache the schema
            self._table_schemas[table_name] = schema

            # Cache foreign key relationships
            self._cache_foreign_keys(table_name, foreign_keys)

            return schema

        except Exception as e:
            logger.error(f"Error getting schema for table {table_name}: {str(e)}")
            return {}

    def _cache_foreign_keys(self, table_name: str, foreign_keys: List[Dict[str, Any]]) -> None:
        """
        Cache foreign key relationships for a table.

        Args:
            table_name: Name of the table
            foreign_keys: List of foreign key dictionaries from SQLAlchemy
        """
        if not table_name in self._foreign_keys:
            self._foreign_keys[table_name] = {}

        for fk in foreign_keys:
            for i, col in enumerate(fk['constrained_columns']):
                referred_table = fk['referred_table']
                referred_col = fk['referred_columns'][i] if i < len(fk['referred_columns']) else fk['referred_columns'][0]

                self._foreign_keys[table_name][col] = {
                    "referred_table": referred_table,
                    "referred_column": referred_col
                }

                # Load reference data for this foreign key
                self._load_reference_data(table_name, col, referred_table, referred_col)

    def _load_reference_data(self, table_name: str, column: str, referred_table: str, referred_column: str) -> None:
        """
        Load reference data for a foreign key relationship.

        Args:
            table_name: Name of the table with the foreign key
            column: Name of the foreign key column
            referred_table: Name of the referenced table
            referred_column: Name of the referenced column
        """
        try:
            # Special handling for department references
            if referred_table == 'department' and referred_column == 'department_identifier':
                # Get the display column (department_name)
                display_column = 'department_name'

                # Create a unique key for this reference
                ref_key = f"{table_name}.{column}"

                # Check if we already have this data
                if ref_key in self._reference_data:
                    return

                # Query the database for reference data
                with self.engine.connect() as connection:
                    query = f"SELECT {referred_column}, {display_column} FROM {referred_table}"
                    result = connection.execute(text(query))

                    # Build a mapping of display values to IDs
                    display_to_id = {}
                    id_to_display = {}

                    for row in result:
                        id_val = row[0]
                        display_val = row[1]

                        # Store case-insensitive versions of the department name
                        if isinstance(display_val, str):
                            # Store the exact case version
                            display_to_id[display_val] = id_val
                            # Store the lowercase version
                            display_to_id[display_val.lower()] = id_val
                            # Store the title case version
                            display_to_id[display_val.title()] = id_val
                        else:
                            display_to_id[display_val] = id_val

                        id_to_display[id_val] = display_val

                    # Cache the reference data
                    self._reference_data[ref_key] = {
                        "display_column": display_column,
                        "display_to_id": display_to_id,
                        "id_to_display": id_to_display
                    }

                    # Print the loaded reference data for debugging
                    print(f"\nLoaded department reference data:")
                    print(f"  Table: {referred_table}")
                    print(f"  Foreign key: {table_name}.{column} -> {referred_table}.{referred_column}")
                    print(f"  Entries: {len(id_to_display)}")
                    if id_to_display:
                        print("  Department mappings:")
                        for id_val, name in id_to_display.items():
                            print(f"    ID {id_val} = '{name}'")

                    logger.info(f"Loaded reference data for {ref_key}: {len(id_to_display)} entries")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error loading reference data for {table_name}.{column}: {error_msg}")
            print(f"Error loading reference data for {table_name}.{column}: {error_msg}")

    def get_display_value_for_foreign_key(self, table_name: str, column: str, id_value: Any) -> Optional[str]:
        """
        Get the display value for a foreign key ID.

        Args:
            table_name: Name of the table with the foreign key
            column: Name of the foreign key column
            id_value: The ID value to look up

        Returns:
            The display value, or None if not found
        """
        ref_key = f"{table_name}.{column}"

        if ref_key not in self._reference_data:
            return None

        ref_data = self._reference_data[ref_key]

        # Try to convert the ID to the right type
        try:
            id_value = int(id_value)
        except (ValueError, TypeError):
            pass

        return ref_data["id_to_display"].get(id_value)

    def get_id_for_display_value(self, table_name: str, column: str, display_value: str) -> Optional[Any]:
        """
        Get the ID for a display value.

        Args:
            table_name: Name of the table with the foreign key
            column: Name of the foreign key column
            display_value: The display value to look up

        Returns:
            The ID value, or None if not found
        """
        ref_key = f"{table_name}.{column}"

        if ref_key not in self._reference_data:
            logger.warning(f"No reference data found for {ref_key}")
            # Try to load the reference data
            if column == "department_identifier":
                self._load_reference_data(table_name, column, "department", "department_identifier")
                if ref_key not in self._reference_data:
                    logger.error(f"Failed to load reference data for {ref_key}")
                    return None
            else:
                return None

        ref_data = self._reference_data[ref_key]

        # Log the lookup attempt
        logger.info(f"Looking up ID for display value: '{display_value}' in {ref_key}")

        # Try exact match first
        if display_value in ref_data["display_to_id"]:
            id_val = ref_data["display_to_id"][display_value]
            logger.info(f"Found exact match: '{display_value}' -> {id_val}")
            return id_val

        # Try case-insensitive lookup for string values
        if isinstance(display_value, str):
            # Try lowercase
            lower_value = display_value.lower()
            if lower_value in ref_data["display_to_id"]:
                id_val = ref_data["display_to_id"][lower_value]
                logger.info(f"Found lowercase match: '{lower_value}' -> {id_val}")
                return id_val

            # Try title case
            title_value = display_value.title()
            if title_value in ref_data["display_to_id"]:
                id_val = ref_data["display_to_id"][title_value]
                logger.info(f"Found title case match: '{title_value}' -> {id_val}")
                return id_val

            # Try partial matching for department names
            if column == "department_identifier":
                logger.info(f"Trying partial matching for department name: '{display_value}'")
                for key, id_val in ref_data["display_to_id"].items():
                    if isinstance(key, str) and (key.lower().startswith(lower_value) or lower_value.startswith(key.lower())):
                        logger.info(f"Found partial match: '{key}' -> {id_val}")
                        return id_val

        # If we get here, no match was found
        logger.warning(f"No match found for '{display_value}' in {ref_key}")

        # Print available values for debugging
        print(f"\nNo match found for '{display_value}' in {ref_key}")
        print("Available values:")
        for key, id_val in ref_data["display_to_id"].items():
            if isinstance(key, str):
                print(f"  '{key}' -> {id_val}")

        return None

    def _print_foreign_key_relationships(self) -> None:
        """Print foreign key relationships for debugging."""
        try:
            print("\n" + "="*80)
            print("FOREIGN KEY RELATIONSHIPS (InsertQueryHandler):")
            print("="*80)

            # Test database connection first
            try:
                with self.engine.connect() as connection:
                    connection.execute(text("SELECT 1"))
                    print("Database connection test: SUCCESS")
            except Exception as e:
                print(f"Database connection test: FAILED - {str(e)}")
                print(f"Cannot retrieve foreign key relationships without database connection")
                print("="*80 + "\n")
                return

            inspector = inspect(self.engine)

            # Get all tables
            try:
                tables = inspector.get_table_names()
                if not tables:
                    print("No tables found in the database!")
                    print("="*80 + "\n")
                    return

                print(f"Found {len(tables)} tables: {', '.join(tables)}")
            except Exception as e:
                print(f"Error getting table names: {str(e)}")
                print("="*80 + "\n")
                return

            fk_found = False
            for table_name in tables:
                try:
                    foreign_keys = inspector.get_foreign_keys(table_name)
                    if foreign_keys:
                        fk_found = True
                        print(f"\nTable: {table_name}")
                        for fk in foreign_keys:
                            referred_table = fk['referred_table']
                            constrained_cols = fk['constrained_columns']
                            referred_cols = fk['referred_columns']
                            print(f"  {constrained_cols[0]} -> {referred_table}.{referred_cols[0]}")

                            # Load this foreign key relationship
                            for i, col in enumerate(constrained_cols):
                                referred_col = referred_cols[i] if i < len(referred_cols) else referred_cols[0]
                                self._load_reference_data(table_name, col, referred_table, referred_col)

                                # Print the reference data if available
                                ref_key = f"{table_name}.{col}"
                                if ref_key in self._reference_data:
                                    ref_data = self._reference_data[ref_key]
                                    print(f"    Reference data loaded: {len(ref_data['display_to_id'])} entries")

                                    # Print a few sample entries
                                    if ref_data['display_to_id']:
                                        print("    Sample mappings:")
                                        count = 0
                                        for display, id_val in ref_data['display_to_id'].items():
                                            print(f"      '{display}' -> {id_val}")
                                            count += 1
                                            if count >= 5:  # Limit to 5 samples
                                                break
                except Exception as e:
                    print(f"Error processing foreign keys for table {table_name}: {str(e)}")

            if not fk_found:
                print("\nNo foreign key relationships found in the database!")

            print("="*80 + "\n")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error printing foreign key relationships: {error_msg}")
            print(f"Error printing foreign key relationships: {error_msg}")
            print("="*80 + "\n")

    def generate_complete_query(self, analysis: Dict[str, Any], user_inputs: Dict[str, str]) -> str:
        """
        Generate a complete INSERT query with user-provided values.

        Args:
            analysis: The query analysis from analyze_insert_query
            user_inputs: Dict mapping column names to user-provided values

        Returns:
            Complete SQL INSERT query
        """
        try:
            if not analysis.get("is_valid", False):
                logger.warning(f"Cannot generate complete query: analysis is not valid")
                return analysis.get("query", "")

            table_name = analysis["table_name"]
            columns = list(analysis["columns"]) if "columns" in analysis else []  # Make a copy
            values = list(analysis["values"]) if "values" in analysis else []    # Make a copy

            logger.info(f"Generating complete query for table: {table_name}")
            logger.info(f"Initial columns: {columns}")
            logger.info(f"Initial values: {values}")
            logger.info(f"User inputs: {user_inputs}")

            # Get table schema for type information
            table_schema = self._get_table_schema(table_name)
            if not table_schema:
                logger.warning(f"Could not get schema for table: {table_name}")

            # Add missing required columns
            for missing in analysis.get("missing_required", []):
                col_name = missing["name"]
                if col_name in user_inputs:
                    # Only add if not already in columns
                    if col_name not in columns:
                        columns.append(col_name)
                        values.append(self._format_value(user_inputs[col_name], missing["type"]))
                        logger.info(f"Added missing required column: {col_name} = {user_inputs[col_name]}")

            # Update missing values
            for i, col in enumerate(columns):
                if i >= len(values) or not values[i] or values[i].upper() == "NULL" or values[i] == "?":
                    if col in user_inputs:
                        # Get column type and other info from schema or missing values
                        col_type = "unknown"
                        is_foreign_key = False
                        fk_info = None

                        # Try to get info from missing values first
                        for missing in analysis.get("missing_values", []):
                            if missing["name"] == col:
                                col_type = missing["type"]
                                is_foreign_key = missing.get("is_foreign_key", False)
                                if is_foreign_key:
                                    fk_info = {
                                        "referred_table": missing.get("referred_table"),
                                        "referred_column": missing.get("referred_column"),
                                        "display_name": missing.get("display_name")
                                    }
                                break

                        # If not found, try to get from schema
                        if col in table_schema:
                            if col_type == "unknown":
                                col_type = str(table_schema[col]["type"])

                            if not is_foreign_key:
                                is_foreign_key = table_schema[col].get("is_foreign_key", False)
                                if is_foreign_key and not fk_info:
                                    schema_fk_info = table_schema[col].get("foreign_key_info")
                                    if schema_fk_info:
                                        fk_info = {
                                            "referred_table": schema_fk_info.get("referred_table"),
                                            "referred_column": schema_fk_info.get("referred_columns", [""])[0],
                                            "display_name": None
                                        }

                        # Handle foreign keys
                        if is_foreign_key and fk_info and fk_info["referred_table"] == "department":
                            # For department references, convert department name to ID
                            department_name = user_inputs[col]
                            department_id = self.get_id_for_display_value(table_name, col, department_name)

                            if department_id is not None:
                                logger.info(f"Converted department name '{department_name}' to ID {department_id}")
                                formatted_value = str(department_id)
                            else:
                                # If department name not found, try to use the value directly
                                # (it might already be an ID)
                                try:
                                    # Check if it's a valid number
                                    department_id = int(department_name)
                                    formatted_value = str(department_id)
                                    logger.info(f"Using department ID directly: {department_id}")
                                except ValueError:
                                    # Not a valid ID, use NULL or default value
                                    formatted_value = "NULL"
                                    logger.warning(f"Department name '{department_name}' not found, using NULL")
                        else:
                            # Regular value formatting
                            formatted_value = self._format_value(user_inputs[col], col_type)

                        # Update or append the value
                        if i < len(values):
                            values[i] = formatted_value
                        else:
                            values.append(formatted_value)

                        logger.info(f"Updated column value: {col} = {formatted_value} (type: {col_type})")

            # Ensure columns and values have the same length
            if len(columns) != len(values):
                logger.warning(f"Column and value count mismatch: {len(columns)} columns, {len(values)} values")
                # Adjust by adding NULL values if needed
                while len(values) < len(columns):
                    values.append("NULL")
                # Or truncate values if there are too many
                if len(values) > len(columns):
                    values = values[:len(columns)]

            # Generate the complete query
            columns_str = ", ".join(columns)
            values_str = ", ".join(values)
            query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({values_str})"

            logger.info(f"Generated complete query: {query}")
            return query

        except Exception as e:
            logger.error(f"Error generating complete query: {str(e)}")
            return analysis.get("query", "")

    def _format_value(self, value: str, col_type: str) -> str:
        """
        Format a value based on its column type.

        Args:
            value: The value to format
            col_type: The SQL type of the column

        Returns:
            Formatted value for SQL
        """
        # Handle NULL values
        if not value or value.upper() == "NULL":
            return "NULL"

        # Trim whitespace
        value = value.strip()

        # Log the formatting
        logger.info(f"Formatting value: '{value}' for column type: {col_type}")

        # Handle date and timestamp types
        if any(date_type in col_type.lower() for date_type in ["date", "time", "timestamp"]):
            # If already quoted, return as is
            if value.startswith("'") and value.endswith("'"):
                return value

            # Try to parse as date/time
            try:
                # Simple validation - check if it has expected date/time format
                if re.match(r'\d{4}-\d{2}-\d{2}', value):  # YYYY-MM-DD format
                    return f"'{value}'"
                elif re.match(r'\d{2}/\d{2}/\d{4}', value):  # MM/DD/YYYY format
                    # Convert to ISO format
                    parts = value.split('/')
                    iso_date = f"{parts[2]}-{parts[0]}-{parts[1]}"
                    return f"'{iso_date}'"
                else:
                    # If it doesn't match expected formats, quote it anyway
                    return f"'{value}'"
            except Exception:
                # If parsing fails, just quote the value
                return f"'{value}'"

        # Handle numeric types
        if any(num_type in col_type.lower() for num_type in ["int", "float", "numeric", "decimal", "double", "real"]):
            try:
                # Check if it's a valid number
                float(value)
                return value
            except ValueError:
                # Not a valid number, treat as string
                return f"'{value}'"

        # Handle boolean
        if "boolean" in col_type.lower() or "bool" in col_type.lower():
            if value.lower() in ["true", "t", "yes", "y", "1"]:
                return "TRUE"
            elif value.lower() in ["false", "f", "no", "n", "0"]:
                return "FALSE"
            else:
                return f"'{value}'"

        # Handle already quoted values
        if (value.startswith("'") and value.endswith("'")) or (value.startswith('"') and value.endswith('"')):
            return value

        # Default to string with proper escaping
        escaped_value = value.replace("'", "''")
        return f"'{escaped_value}'"
