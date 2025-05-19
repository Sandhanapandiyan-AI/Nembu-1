import logging
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError
from .config import DATABASE_URL

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self):
        try:
            self.engine = create_engine(DATABASE_URL)
            logger.info(" Initialized Database Service with PostgreSQL")

            # Test the connection
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
                logger.info(" Database connection test successful")

            # Print the connection details
            print(f"\nDATABASE CONNECTION INFO:")
            print(f"URL: {DATABASE_URL}")

            # Print the tables in the database
            inspector = inspect(self.engine)
            tables = inspector.get_table_names()
            print(f"Tables found in database: {len(tables)}")
            if tables:
                print("Table list:")
                for table in tables:
                    print(f"  - {table}")
            else:
                print("WARNING: No tables found in the database!")

        except Exception as e:
            logger.error(f" Error initializing database service: {str(e)}")
            print(f"\nDATABASE CONNECTION ERROR: {str(e)}")
            print(f"Check your database configuration in config.py")
            print(f"Current DATABASE_URL: {DATABASE_URL}")

    def execute_query(self, query: str) -> Dict[str, Any]:
        """Execute a SQL query and return the results in a formatted way."""
        try:
            logger.info(f"🔍 Executing SQL query: {query}")

            # Check if this is a data modification query (UPDATE, INSERT, DELETE)
            is_modification_query = False
            query_type = ""
            if query.strip().upper().startswith("UPDATE"):
                is_modification_query = True
                query_type = "UPDATE"
            elif query.strip().upper().startswith("INSERT"):
                is_modification_query = True
                query_type = "INSERT"
            elif query.strip().upper().startswith("DELETE"):
                is_modification_query = True
                query_type = "DELETE"

            with self.engine.connect() as connection:
                # Start a transaction
                trans = connection.begin()
                try:
                    result = connection.execute(text(query))

                    # For data modification queries, get the row count and commit
                    if is_modification_query:
                        row_count = result.rowcount
                        trans.commit()

                        logger.info(f" {query_type} query executed successfully. Affected {row_count} rows")
                        return {
                            "success": True,
                            "query_type": query_type,
                            "row_count": row_count,
                            "columns": [],
                            "results": [],
                            "message": f"{query_type} operation successful. {row_count} rows affected.",
                            "error": None
                        }

                    # For SELECT queries, fetch the results
                    else:
                        # Get column names
                        columns = result.keys()

                        # Fetch all rows
                        rows = result.fetchall()

                        # Convert rows to list of dicts for easier handling
                        results = [dict(zip(columns, row)) for row in rows]

                        # Check if this is an employee query and enhance with department names
                        if any('employee' in col.lower() for col in columns):
                            results = self.enhance_employee_data(results)
                            # Update columns to include department_name if it was added
                            if results and 'department_name' in results[0] and 'department_name' not in columns:
                                columns = list(columns) + ['department_name']

                        # Format response
                        response = {
                            "success": True,
                            "query_type": "SELECT",
                            "row_count": len(results),
                            "columns": columns,
                            "results": results,
                            "error": None
                        }

                        logger.info(f" SELECT query executed successfully. Retrieved {len(results)} rows")
                        return response
                except Exception as e:
                    # Rollback the transaction if there's an error
                    trans.rollback()
                    raise e

        except SQLAlchemyError as e:
            error_msg = str(e)
            logger.error(f" Database error: {error_msg}")
            return {
                "success": False,
                "query_type": "ERROR",
                "row_count": 0,
                "columns": [],
                "results": [],
                "error": error_msg
            }

    def format_results_as_markdown(self, query_results: Dict[str, Any]) -> str:
        """Format query results as a markdown table for chat display."""
        if not query_results["success"]:
            return f" Error executing query: {query_results['error']}"

        # Handle data modification queries (UPDATE, INSERT, DELETE)
        if "query_type" in query_results and query_results["query_type"] in ["UPDATE", "INSERT", "DELETE"]:
            return f" {query_results['message']}"

        # Handle SELECT queries with no results
        if query_results["row_count"] == 0:
            return "ℹ No results found for this query."

        # Handle SELECT queries with results
        columns = query_results["columns"]
        rows = query_results["results"]

        # Create header
        markdown = f" Found {query_results['row_count']} results:\n\n"

        # Add table header
        markdown += "| " + " | ".join(str(col) for col in columns) + " |\n"
        markdown += "|-" + "-|-".join("-" * len(str(col)) for col in columns) + "-|\n"

        # Add rows
        for row in rows:
            markdown += "| " + " | ".join(str(row[col]) for col in columns) + " |\n"

        return markdown

    def get_results_as_json(self, query_results: Dict[str, Any]) -> Dict[str, Any]:
        """Return the query results in a structured JSON format."""
        if not query_results["success"]:
            return {
                "success": False,
                "error": query_results["error"],
                "data": None
            }

        # Handle data modification queries (UPDATE, INSERT, DELETE)
        if "query_type" in query_results and query_results["query_type"] in ["UPDATE", "INSERT", "DELETE"]:
            return {
                "success": True,
                "query_type": query_results["query_type"],
                "message": query_results["message"],
                "affected_rows": query_results["row_count"],
                "data": None
            }

        # Handle SELECT queries with no results
        if query_results["row_count"] == 0:
            return {
                "success": True,
                "query_type": "SELECT",
                "message": "No results found for this query.",
                "data": {
                    "columns": [],
                    "rows": []
                }
            }

        # Handle SELECT queries with results
        return {
            "success": True,
            "query_type": "SELECT",
            "message": f"Found {query_results['row_count']} results",
            "data": {
                "columns": list(query_results["columns"]),
                "rows": query_results["results"]
            }
        }

    def get_departments(self) -> Dict[int, str]:
        """Get a mapping of department IDs to department names."""
        try:
            with self.engine.connect() as connection:
                result = connection.execute(text("SELECT department_identifier, department_name FROM department"))
                departments = {row[0]: row[1] for row in result.fetchall()}
                return departments
        except SQLAlchemyError as e:
            logger.error(f" Error fetching departments: {str(e)}")
            return {}

    def enhance_employee_data(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enhance employee data with department names."""
        if not results:
            return results

        # Check if this is employee data with department_identifier
        if not all('department_identifier' in row for row in results):
            return results

        # Get department mapping
        departments = self.get_departments()
        if not departments:
            return results

        # Enhance each row with department name
        enhanced_results = []
        for row in results:
            enhanced_row = row.copy()
            dept_id = row.get('department_identifier')
            if dept_id in departments:
                enhanced_row['department_name'] = departments[dept_id]
            else:
                enhanced_row['department_name'] = 'Unknown'
            enhanced_results.append(enhanced_row)

        return enhanced_results

    def get_database_schema(self) -> str:
        """Fetch the database schema including tables, columns, and their types."""
        try:
            print("\n" + "="*80)
            print("FETCHING DATABASE SCHEMA...")
            print("="*80)

            inspector = inspect(self.engine)
            schema_info = []

            # Get all tables
            tables = inspector.get_table_names()
            if not tables:
                error_msg = "No tables found in the database!"
                print(f"ERROR: {error_msg}")
                return error_msg

            print(f"Found {len(tables)} tables: {', '.join(tables)}")

            for table_name in tables:
                print(f"Processing table: {table_name}")
                try:
                    columns = inspector.get_columns(table_name)
                    foreign_keys = inspector.get_foreign_keys(table_name)
                    primary_key = inspector.get_pk_constraint(table_name)

                    print(f"  - Columns: {len(columns)}")
                    print(f"  - Foreign keys: {len(foreign_keys)}")
                    print(f"  - Primary key: {primary_key['constrained_columns'] if primary_key['constrained_columns'] else 'None'}")

                    # Get sample data for reference tables
                    sample_data = ""
                    if table_name == "department":
                        try:
                            with self.engine.connect() as connection:
                                result = connection.execute(text(f"SELECT department_identifier, department_name FROM {table_name} LIMIT 10"))
                                rows = result.fetchall()
                                if rows:
                                    sample_data = "\n    Sample data:\n"
                                    for row in rows:
                                        sample_data += f"      {row[0]}: {row[1]}\n"
                                    print(f"  - Sample data: {len(rows)} rows")
                        except Exception as e:
                            error_msg = str(e)
                            logger.error(f"Error fetching sample data for {table_name}: {error_msg}")
                            print(f"  - Error fetching sample data: {error_msg}")

                    # Format column information
                    column_info = []
                    for col in columns:
                        constraints = []
                        if col['name'] in primary_key['constrained_columns']:
                            constraints.append('PRIMARY KEY')
                        if col.get('nullable') is False:
                            constraints.append('NOT NULL')
                        if col.get('autoincrement', False):
                            constraints.append('AUTO INCREMENT')

                        column_desc = f"    {col['name']} {str(col['type'])}"
                        if constraints:
                            column_desc += f" ({', '.join(constraints)})"
                        column_info.append(column_desc)

                    # Format foreign key information
                    for fk in foreign_keys:
                        referred_table = fk['referred_table']
                        constrained_cols = fk['constrained_columns']
                        referred_cols = fk['referred_columns']
                        column_info.append(f"    FOREIGN KEY ({', '.join(constrained_cols)}) REFERENCES {referred_table}({', '.join(referred_cols)})")

                    # Add table schema to the list
                    schema_info.append(f"Table: {table_name}\n" + "\n".join(column_info) + sample_data)

                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"Error processing table {table_name}: {error_msg}")
                    print(f"  - Error processing table: {error_msg}")
                    schema_info.append(f"Table: {table_name}\n    Error: {error_msg}")

            # Combine all schema information
            full_schema = "\n\n".join(schema_info)

            # Print the schema to the terminal
            print("\n" + "="*80)
            print("DETAILED DATABASE SCHEMA:")
            print("="*80)
            print(full_schema)

            # Also print foreign key relationships
            fk_info = []
            for table_name in tables:
                try:
                    foreign_keys = inspector.get_foreign_keys(table_name)
                    for fk in foreign_keys:
                        referred_table = fk['referred_table']
                        constrained_cols = fk['constrained_columns']
                        referred_cols = fk['referred_columns']
                        fk_info.append(f"{table_name}.{constrained_cols[0]} -> {referred_table}.{referred_cols[0]}")
                except Exception as e:
                    logger.error(f"Error getting foreign keys for {table_name}: {str(e)}")

            if fk_info:
                print("\nForeign Key Relationships:")
                for fk in fk_info:
                    print(f"  {fk}")
                print()

            logger.info(" Successfully retrieved database schema")
            return full_schema

        except Exception as e:
            error_msg = str(e)
            logger.error(f" Error fetching database schema: {error_msg}")
            print(f"ERROR fetching database schema: {error_msg}")
            return f"Error fetching schema: {error_msg}"
