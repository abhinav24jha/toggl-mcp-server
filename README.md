# Toggl MCP Server

Allows MCP clients to interact with Toggl Track, enabling time tracking, project management, and workspace operations through natural language.

## Features

### Tools

#### Project Management
- **create_project**
  - **Description**: Creates a new project in a specified Toggl workspace.
  - **Input**:
    - `name` (str): The name of the project to be created. This is a required field.
    - `workspace_name` (str, optional): The name of the workspace where the project will be created. If not provided, it defaults to the user's default workspace.
    - `active` (bool, optional): Specifies whether the project is active. Defaults to `True`.
    - `billable` (bool, optional): Specifies whether the project is billable. Defaults to `False`.
    - `client_id` (int, optional): The ID of the client associated with the project.
    - `color` (str, optional): The hex color code assigned to the project (e.g., "#FF0000").
    - `is_private` (bool, optional): Specifies whether the project is private. Defaults to `True`.
    - `start_date` (str, optional): The start date of the project in ISO 8601 format (e.g., "YYYY-MM-DD").
    - `end_date` (str, optional): The end date of the project in ISO 8601 format (e.g., "YYYY-MM-DD").
    - `estimated_hours` (int, optional): The estimated number of hours for the project.
    - `template` (bool, optional): Specifies whether the project is a template. Defaults to `False`.
    - `template_id` (int, optional): The ID of the template to use for creating the project.
  - **Output**: JSON response containing the data of the newly created project.

- **delete_project**
  - **Description**: Deletes a project identified by its name within a specified workspace.
  - **Input**:
    - `project_name` (str): The exact name of the project to be deleted. This is a required field.
    - `workspace_name` (str, optional): The name of the workspace containing the project. If not provided, it defaults to the user's default workspace.
  - **Output**: A confirmation message (str) indicating the successful deletion of the project.

- **update_projects**
  - **Description**: Performs bulk updates on multiple projects within a specified workspace using patch operations.
  - **Input**:
    - `project_names` (List[str]): A list containing the names of the projects to be updated. This is a required field.
    - `operations` (List[dict]): A list of patch operations to apply to the selected projects. Each operation is a dictionary specifying the operation type (`op`), the field path (`path`), and the new value (`value`) (e.g., `{"op": "replace", "path": "/active", "value": false}`). This is a required field.
    - `workspace_name` (str, optional): The name of the workspace containing the projects. If not provided, it defaults to the user's default workspace.
  - **Output**: JSON response containing the data of the updated projects.

- **get_all_projects**
  - **Description**: Retrieves a list of all projects within a specified workspace.
  - **Input**:
    - `workspace_name` (str, optional): The name of the workspace from which to retrieve projects. If not provided, it defaults to the user's default workspace.
  - **Output**: JSON response containing a list of project data objects found in the specified workspace.

#### Time Entry Management
- **new_time_entry**
  - **Description**: Creates a new time entry. Can be used to start a timer (if only `start` is provided or neither `start` nor `duration` are provided) or log a completed time entry (if `start` and `stop`, or `start` and `duration` are provided).
  - **Input**:
    - `description` (str): The description for the time entry.
    - `workspace_name` (str, optional): Name of the workspace. Defaults to the user's default workspace.
    - `project_name` (str, optional): Name of the project to associate the time entry with.
    - `tags` (List[str], optional): A list of tag names to apply to the time entry.
    - `start` (str, optional): The start time of the entry in ISO 8601 format (e.g., "2023-10-26T10:00:00Z"). Defaults to the current time if creating a running entry.
    - `stop` (str, optional): The stop time of the entry in ISO 8601 format. If provided, creates a completed entry.
    - `duration` (int, optional): The duration of the entry in seconds. If `start` is provided but `stop` is not, `duration` determines the stop time. If `start` is not provided, a negative duration starts a running timer.
    - `billable` (bool, optional): Whether the time entry should be marked as billable. Defaults to False.
    - `created_with` (str, optional): The name of the application creating the entry. Defaults to "MCP".
  - **Output**: JSON response containing the data of the created time entry.

- **stop_time_entry**
  - **Description**: Stops the currently running time entry.
  - **Input**:
    - `workspace_name` (str, optional): Name of the workspace where the entry is running. Defaults to the user's default workspace.
  - **Output**: JSON response containing the data of the stopped time entry.

- **delete_time_entry**
  - **Description**: Deletes a specific time entry by its description and start time.
  - **Input**:
    - `time_entry_description` (str): The exact description of the time entry to delete.
    - `start_time` (str): The exact start time of the entry in ISO 8601 format used for identification.
    - `workspace_name` (str, optional): Name of the workspace containing the entry. Defaults to the user's default workspace.
  - **Output**: Success confirmation message (str) upon successful deletion.

- **get_current_time_entry**
  - **Description**: Fetches the details of the currently running time entry.
  - **Input**: None (implicitly uses the user's context).
  - **Output**: JSON response containing the data of the currently running time entry, or None if no time entry is currently running.

- **update_time_entry**
  - **Description**: Updates attributes of an existing time entry identified by its description and start time.
  - **Input**:
    - `time_entry_description` (str): The current description of the time entry to update.
    - `start_time` (str): The exact start time of the entry in ISO 8601 format used for identification.
    - `workspace_name` (str, optional): Name of the workspace containing the entry. Defaults to the user's default workspace.
    - `new_description` (str, optional): New description for the time entry.
    - `project_name` (str, optional): New project name to associate with the entry. Set to empty string "" to remove project association.
    - `tags` (List[str], optional): A new list of tag names. This will replace all existing tags. Provide an empty list `[]` to remove all tags.
    - `new_start` (str, optional): New start time in ISO 8601 format.
    - `new_stop` (str, optional): New stop time in ISO 8601 format.
    - `billable` (bool, optional): New billable status.
  - **Output**: JSON response containing the data of the updated time entry.

- **get_time_entries_for_range**
  - **Description**: Retrieves time entries within a specified date range, defined by offsets from the current day.
  - **Input**:
    - `from_day_offset` (int): The start day offset from today (e.g., 0 for today, -1 for yesterday, -7 for a week ago).
    - `to_day_offset` (int): The end day offset from today (e.g., 0 for today, 1 for tomorrow). The range includes both the start and end dates.
    - `workspace_name` (str, optional): Name of the workspace to fetch entries from. Defaults to the user's default workspace.
  - **Output**: JSON response containing a list of time entries found within the specified date range.

## Getting Started

### Prerequisites
- Python 3.11+
- Toggl Track account
- uv installed for dependency management

### Environment Variables
Create a `.env` file inside of the `mcp_toggl_server` folder with:
```bash
EMAIL=your_toggl_email
PASSWORD=your_toggl_password
```

If you are using Toggl API tokens:
```bash
EMAIL=xxxx
PASSWORD="api_token"
```
Where `xxxx` indicates your personal token

### Installation

First install uv:
    - For MacOS/Linux:
        ```bash
        curl -LsSf https://astral.sh/uv/install.sh | sh
        ```
    - For Windows:
        ```bash
        powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
        ```

Make sure to restart your terminal afterwards to ensure that the uv command gets picked up.

Now let's clone the repository and set up the project:

```bash
git clone [repository-url]
cd mcp_toggl_server
uv venv
uv pip install --all
```

### Integration with Development Tools

#### VS Code + GitHub Copilot Setup

1. Configure the MCP Server in `.vscode/mcp.json`:
```json
"servers": {
  "toggl": {
    "type": "stdio",
    "command": "uv",
    "args": [
      "--directory",
      "/ABSOLUTE/PATH/TO/PARENT/FOLDER/mcp_toggl_server",
      "run",
      "toggl_mcp_server.py"],
    "envFile": "${workspaceFolder}/mcp_toggl_server/.env"
  }
}
```

2. Update the configuration:
   - Replace `/ABSOLUTE/PATH/TO/PARENT/FOLDER/mcp_toggl_server` with the absolute path to the server
   - You may need to put the full path to the uv executable in the command field. You can get this by running which uv on MacOS/Linux or where uv on Windows

3. Enable the server:
   - Look for the start button when hovering over the server configuration `/.vscode/mcp.json`
   - Click start to let Copilot discover available tools
   - Switch to agent mode in Copilot

For detailed setup instructions, see:
- [MCP Servers in VS Code](https://code.visualstudio.com/docs/copilot/chat/mcp-servers)
- [Copilot Agent Mode](https://code.visualstudio.com/docs/copilot/chat/chat-agent-mode)

### Additional MCP Client Integration

The Toggl MCP Server works with any MCP-compatible client. For integration steps:

1. For Claude Desktop, visit the [MCP Quick Start Guide](https://modelcontextprotocol.io/quickstart/user)
2. For other MCP clients, consult their respective documentation for server configuration

Note: Configuration typically involves specifying the server path and environment variables similar to the VS Code setup above.

### Testing with MCP Inspector
To run in development:
```bash
EMAIL=your_toggl_email PASSWORD=your_toggl_password mcp dev toggl_mcp_server.py
```

## License

This MCP server is licensed under the MIT License.