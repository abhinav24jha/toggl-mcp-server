from typing import Any, List, Union, Tuple, Optional, Literal
import httpx
import os
import datetime
from datetime import timezone, timedelta
from base64 import b64encode
from tzlocal import get_localzone
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

auth_email = os.getenv("EMAIL")
auth_password = os.getenv("PASSWORD") 

mcp = FastMCP("toggl")

auth_credentials = f"{os.getenv('EMAIL')}:{os.getenv('PASSWORD')}".encode('utf-8')
auth_header = f"Basic {b64encode(auth_credentials).decode('ascii')}"

headers={
    "Content-Type": "application/json",
    "Authorization": auth_header 
}

TOGGL_COLORS = Literal[
    "#4dc3ff",  # Light Blue
    "#bc85e6",  # Lavender
    "#df7baa",  # Pink
    "#f68d38",  # Orange
    "#b27636",  # Brown
    "#8ab734",  # Lime Green
    "#14a88e",  # Teal
    "#268bb5",  # Medium Blue
    "#6668b4",  # Purple
    "#a4506c",  # Rose
    "#67412c",  # Dark Brown
    "#3c6526",  # Forest Green
    "#094558",  # Navy Blue
    "#bc2d07",  # Red
    "#999999"   # Gray
]

########################
# HELPERS - TIME Specific
########################

def _get_current_utc_time() -> str:
    """
    Get the current UTC time formatted as an ISO 8601 timestamp with milliseconds and 'Z' suffix.
    
    Returns:
        str: The current UTC time in RFC 3339 format. Example: '2025-04-09T16:15:22.000Z'
    
    This format is strictly required by the Toggl Track API for the `start` field in time entry creation.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.000Z")

def _convert_utc_to_local(utc_iso_time: str) -> str:
    """
    Convert an RFC 3339 UTC timestamp string to the local system time and format it with timezone.

    Args:
        utc_iso_time (str): A UTC timestamp string (e.g., '2025-04-09T15:37:50.000Z').

    Returns:
        str: A human-readable local time string with timezone info. 
             Example: '2025-04-09 21:07:50 IST'
    """
    try:
        if "." in utc_iso_time:
            utc_time = datetime.datetime.strptime(utc_iso_time, "%Y-%m-%dT%H:%M:%S.%fZ")
        else:
            utc_time = datetime.datetime.strptime(utc_iso_time, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as e:
        return f"Invalid timestamp format: {e}"

    utc_time = utc_time.replace(tzinfo=datetime.timezone.utc)
    local_tz = get_localzone()
    local_time = utc_time.astimezone(local_tz)
    return local_time.strftime("%Y-%m-%d %H:%M:%S %Z")

def _iso_timestamp(dt: datetime.datetime) -> str:
    """Convert a datetime to ISO 8601 format with milliseconds and 'Z' suffix."""
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")

def _get_date_range(days_offset: int) -> Tuple[str, str]:
    """
    Returns start and end ISO timestamps for a given day.
    
    days_offset = 0: today
    days_offset = -1: yesterday
    """
    # get UTC date today at midnight
    today_utc = datetime.datetime.utcnow().date()
    target_date = today_utc + timedelta(days=days_offset)
    start_dt = datetime.datetime.combine(target_date, datetime.time.min, tzinfo=timezone.utc)
    end_dt = start_dt + timedelta(days=1)
    return _iso_timestamp(start_dt), _iso_timestamp(end_dt)


########################
# HELPERS - Tools Specific
########################

async def _create_project_helper(
    name: str,
    workspace_id: int,
    active: Optional[bool] = True,
    billable: Optional[bool] = False,
    client_id: Optional[int] = None,
    color: Optional[str] = None,
    is_private: Optional[bool] = True,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    estimated_hours: Optional[int] = None,
    template: Optional[bool] = False,
    template_id: Optional[int] = None
) -> Union[dict, str]:
    """
    Helper function to create a new project in a Toggl workspace.

    Args:
        name (str): Name of the project to create
        workspace_id (int): ID of the workspace to create the project in
        active (bool, optional): Whether project is active. Defaults to True
        billable (bool, optional): Whether project is billable. Defaults to False
        client_id (int, optional): Associated client ID
        color (str, optional): Project color hex code
        is_private (bool, optional): Whether project is private. Defaults to True
        start_date (str, optional): Project start date in ISO format
        end_date (str, optional): Project end date in ISO format
        estimated_hours (int, optional): Estimated project hours
        template (bool, optional): Whether this is a template. Defaults to False
        template_id (int, optional): ID of template to use

    Returns:
        dict: Project data on success
        str: Error message on failure
    """
    url = f"https://api.track.toggl.com/api/v9/workspaces/{workspace_id}/projects"

    payload = {
        "name": name,
        "active": active,
        "billable": billable,
        "client_id": client_id,
        "color": color,
        "is_private": is_private,
        "start_date": start_date,
        "end_date": end_date,
        "estimated_hours": estimated_hours,
        "template": template,
        "template_id": template_id
    }

    # Remove None values
    payload = {k: v for k, v in payload.items() if v is not None}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                return "User does not have access to this resource"
            elif e.response.status_code == 500:
                return "Internal Server Error"
            return f"HTTP error: {e.response.status_code}"
        except Exception as e:
            return f"Error: {str(e)}"

async def _delete_project_helper(project_id: int, workspace_id: int) -> Union[int, str]:
    """
    Sends a DELETE request to remove a project from the specified Toggl workspace.

    Args:
        project_id (int): The ID of the project to delete.
        workspace_id (int, optional): The Toggl workspace ID. Defaults to 8631153.

    Returns:
        int: HTTP status code 200 on successful deletion.
        str: Error message string if deletion fails.
    """
    url = f"https://api.track.toggl.com/api/v9/workspaces/{workspace_id}/projects/{project_id}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.delete(url, headers=headers)
            response.raise_for_status()
            return response.status_code
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                return "Invalid project_id"
            elif e.response.status_code == 403:
                return f"Error: {e}"
            elif e.response.status_code == 500:
                return "Internal Server Error"
            return f"HTTP error: {e.response.status_code}"
        except Exception as e:
            return f"Unknown error: {str(e)}"

async def _update_projects_helper(
    workspace_id: int,
    project_ids: List[int],
    operations: List[dict]
) -> Union[dict, str]:
    """
    Bulk update multiple projects in a workspace using PATCH operations.

    Args:
        workspace_id (int): ID of the workspace containing the projects
        project_ids (List[int]): List of project IDs to update
        operations (List[dict]): List of patch operations, each containing:
            - op (str): Operation type ("add", "remove", "replace")
            - path (str): Path to the field (e.g., "/color")
            - value (Any): New value for the field

    Returns:
        dict: Response containing success and failure information
        str: Error message if the request fails
    """
    # Convert project IDs list to comma-separated string
    project_ids_str = ",".join(str(pid) for pid in project_ids)
    
    url = f"https://api.track.toggl.com/api/v9/workspaces/{workspace_id}/projects/{project_ids_str}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.patch(
                url,
                json=operations,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 500:
                return "Internal Server Error"
            return f"HTTP error: {e.response.status_code}"
        except Exception as e:
            return f"Error: {str(e)}"
        
async def _new_time_entry_helper(
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    project_id: Optional[int] = None,
    start: Optional[str] = None,
    stop: Optional[str] = None,
    duration: Optional[int] = -1,
    billable: Optional[bool] = False,
    workspace_id: Optional[int] = None
) -> Union[Tuple[dict, str], str]:
    """
    Creates a new Toggl time entry with flexible support for running or completed tasks.

    This helper supports both real-time tracking (running entry) and backlogged logs (with start/stop/duration). 
    Fields are optional and will only be sent to the API if explicitly provided.

    Args:
        description (str, optional): Activity being tracked (e.g. "Fixing bugs").
        tags (List[str], optional): List of tags to associate.
        project_id (int, optional): Associated project ID.
        start (str, optional): UTC start timestamp (RFC3339).
        stop (str, optional): UTC stop timestamp.
        duration (int, optional): Duration in seconds. Use -1 for running entry.
        billable (bool, optional): Whether the task is billable.
        workspace_id (int): Toggl workspace ID.

    Returns:
        Tuple[dict, str]: API response and system-local time.
        str: Error message on failure.
    """
    if workspace_id is None:
        return "Error: workspace_id must be provided to _new_time_entry_helper."
    
    url = f"https://api.track.toggl.com/api/v9/workspaces/{workspace_id}/time_entries"

    current_iso_time = _get_current_utc_time()
    current_local_time = _convert_utc_to_local(current_iso_time)

    payload = {
        "created_with": "toggl_mcp_server",
        "description": description,
        "tags": tags,
        "project_id": project_id,
        "start": start if start else current_iso_time,
        "stop": stop,
        "duration": duration,
        "billable": billable,
        "workspace_id": workspace_id
    }

    # Remove all None fields
    payload = {k: v for k, v in payload.items() if v is not None}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json(), current_local_time
        except Exception as e:
            return f"Error: {e}"

async def _stopping_time_entry_helper(time_entry_id: int, workspace_id: int) -> Union[dict, str]:
    """
    Sends a PATCH request to stop a running Toggl time entry by its ID.

    This helper function calls the Toggl Track API to stop a time entry, marking the end of a tracked time block. This is useful for time entry automation, enforcing time boundaries, or integrating "stop tracking" commands from natural language queries.

    Args:
        time_entry_id (int): The unique ID of the time entry to stop.
        workspace_id (int, optional): The Toggl workspace ID the time entry belongs to. Defaults to 8631153.

    Returns:
        dict: JSON response from the Toggl API if successful.
        str: An error message if the request fails.
    """
    url = f"https://api.track.toggl.com/api/v9/workspaces/{workspace_id}/time_entries/{time_entry_id}/stop"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.patch(url, headers=headers)

            if 200 <= response.status_code < 300:
                try:
                    return response.json()
                except Exception as json_e:
                    return f"Error parsing successful response: {json_e}"
            else:
                if response.status_code == 404:
                     return f"Stop failed: Time entry not found or already stopped (HTTP 404). Response: {response.text}"
                elif response.status_code == 400:
                     return f"Stop failed: Bad Request (HTTP 400). Possibly already stopped or invalid state. Response: {response.text}"
                else:
                    return f"HTTP error {response.status_code}: {response.text}"

        except httpx.RequestError as req_e: 
            return f"Request failed: {req_e}"
        except Exception as e:
            return f"An unexpected error occurred: {e}"

async def _deleting_time_entry_helper(time_entry_id: int, workspace_id: int) -> Union[dict, str]:
    """
    Sends a DELETE request to remove a specific time entry from the Toggl Track workspace.

    This helper function performs a direct API call to the Toggl backend to permanently delete a time entry by its unique ID.
    It is typically used by higher-level tools that expose user-facing deletion commands, such as:
    - "Delete the entry for 'Writing MCP Docs'"
    - "Remove my last time entry"

    This operation is **irreversible** and should only be triggered after proper verification or user intent confirmation.

    Args:
    - `time_entry_id` (int): The unique ID of the time entry to be deleted.
    - `workspace_id` (int, optional): The Toggl workspace in which the time entry resides. Defaults to `8631153`.

    Returns:
    - `int`: HTTP status code (typically `200` or `204`) if the deletion is successful.
    - `str`: An error message string if deletion fails due to:
        - Authorization issues (`403`)
        - Server-side errors (`500`)
        - Network or client-side failures
    """
    url = f"https://api.track.toggl.com/api/v9/workspaces/{workspace_id}/time_entries/{time_entry_id}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.delete(url, headers=headers)
            response.raise_for_status()
            return response.status_code
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                return "User does not have access to this resource."
            elif e.response.status_code == 500:
                return "Internal Server Error"
            return f"HTTP error: {e.response.status_code}"
        except Exception as e:
            return f"Unknown error: {str(e)}"

async def _get_current_time_entry_helper() -> Union[dict, str]:
    """
    Fetch the currently running time entry for the authenticated Toggl user.

    This helper function queries the Toggl Track API for the active (i.e., currently ongoing) time entry associated with the authenticated user.
    It is useful for determining what the user is currently working on, displaying real-time status, or stopping/modifying the active session.

    Args:
    - None.

    Returns:
    - `dict`: JSON object describing the currently running time entry, or containing `data: None` if none is active.
    - `str`: Descriptive error message if the request fails due to authorization, connectivity, or internal server errors.
    """
    url = "https://api.track.toggl.com/api/v9/me/time_entries/current"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                return "User does not have access to this resource."
            elif e.response.status_code == 404:
                return "Resource can not be found"
            elif e.response.staus_code == 500:
                return "Internal Server Error"
            return f"HTTP error: {e.response.status_code}"
        except Exception as e:
            return f"Unknown error: {str(e)}"

async def _update_time_entry_helper(time_entry_id: int,
                            workspace_id: int, 
                            description: Optional[str] = None,
                            tags: Optional[List[str]] = None, 
                            project_id: Optional[int] = None, 
                            start: Optional[str] = None, 
                            stop: Optional[str] = None,  
                            duration: Optional[int] = None,
                            billable: Optional[bool] = None) -> Union[dict, str]:
    
    """
    Update one or more attributes of an existing time entry in the Toggl Track workspace.

    This helper function performs a partial update of a specified time entry by issuing a `PUT` request to the Toggl API.
    Only the provided fields are modified — any fields left as `None` are excluded from the update payload, preserving their existing values.

    Updatable Fields:
    All parameters are optional (except `time_entry_id` and `workspace_id`). You may provide any combination of the following:
    
    - `description` (str): Updated description of the activity
    - `tags` (List[str]): Updated list of tag names. Toggl will create new tags if needed
    - `project_id` (int): ID of the new associated project
    - `start` (str): ISO 8601 UTC timestamp for the new start time (e.g. `'2025-04-10T08:00:00Z'`)
    - `stop` (str): ISO 8601 UTC timestamp for the new stop time
    - `duration` (int): Duration in seconds. Should be negative (e.g., `-1`) if the entry is still running
    - `billable` (bool): Flag indicating whether the entry is billable

    The `created_with` field is automatically set to `"toggl_mcp_server"` to comply with Toggl's API requirements.

    Args:
    - `time_entry_id` (int): Unique identifier of the time entry to update.
    - `workspace_id` (int, optional): Toggl workspace ID. Defaults to `8631153`.
    - `description`, `tags`, `project_id`, `start`, `stop`, `duration`, `billable`: Optional fields to update.

    Returns:
    - `dict`: JSON response from Toggl if the update succeeds.
    - `str`: Error message string if the update fails due to request issues, auth failure, or malformed data.

    """
    url = f"https://api.track.toggl.com/api/v9/workspaces/{workspace_id}/time_entries/{time_entry_id}"

    payload = {
        "created_with": "toggl_mcp_server",
        "description": description,
        "tags": tags,
        "project_id": project_id,
        "start": start,
        "stop": stop,
        "duration": duration,
        "billable": billable,
    }

    payload = {key: value for key, value in payload.items() if value is not None}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(
                url,
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            print(f"Response json: {response.json}")
            return response.json()
        except Exception as e:
            return f"Error: {e}"

async def _get_default_workspace_id() -> Union[int, str]:
    """
    Retrieve the default workspace ID of the currently authenticated Toggl user.

    This helper sends a GET request to the `/me` endpoint of the Toggl Track API, which returns
    user profile metadata. The function extracts the `default_workspace_id` from the response,
    which is used as the fallback workspace when none is explicitly specified in tool calls.

    Returns:
        int: The default workspace ID if the request succeeds and the value exists.
        str: A descriptive error message if the request fails or the field is missing.
    """
    url = "https://api.track.toggl.com/api/v9/me"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json().get("default_workspace_id")
        except Exception as e:
            return f"Failed to fetch default workspace ID: {str(e)}"

########################
# HELPERS - Resources Specific
########################

async def _get_project_id_by_name(project_name: str, workspace_id: int) -> Union[int, str]:
    """
    Fetches the project ID corresponding to a given project name.
    
    Args:
        project_name (str): The name of the project.
        workspace_id (int): The workspace ID.

    Returns:
        int: The project ID if found.
        str: Error message if not found.
    """
    projects_response = await _get_projects(workspace_id)
    
    if "error" in projects_response:
        return f"Error fetching projects: {projects_response['error']}"
    
    for project in projects_response.get("projects", []):
        if project.get("name") == project_name:
            return project.get("id")
    
    return f"Project with name '{project_name}' doesn't exist"

async def _get_time_entry_id_by_name(time_entry_name: str, workspace_id: int) -> Union[int, str]:
    """
    Retrieve the ID of a time entry based on an exact match of its description.

    This helper searches all user time entries to find one whose description matches the given name exactly.
    It's useful when the user or LLM refers to an entry by name and the corresponding ID is needed for API actions.

    Args:
        time_entry_name (str): The exact description of the time entry (e.g., "Writing MCP Docs").
        workspace_id (int, optional): The Toggl workspace to search in. Defaults to 8631153.

    Returns:
        int: The ID of the matching time entry, if found.
        str: An error message if the entry is not found or if the fetch fails.
    """
    time_entries_response = await _get_time_entries()

    if "error" in time_entries_response:
        return f"Error fetching time_entries: {time_entries_response["error"]}"
    
    for time_entry in time_entries_response:
        if time_entry.get("description") == time_entry_name:
            return time_entry.get("id")
        
    return f"Time entry with name '{time_entry_name}' doesn't exist"

async def _get_workspace_id_by_name(workspace_name: str) -> Union[int, str]:
    """
    Retrieve the ID of a workspace based on its name.
    This helper searches all user workspaces to find one whose name matches the given name exactly.

    Args:
        workspace_name (str): The name of the workspace to search for.
    Returns:
        int: The ID of the matching workspace, if found.
        str: An error message if the workspace is not found or if the fetch fails.
    """
    workspaces_response = await _get_workspaces()
    
    if "error" in workspaces_response:
        return f"Error fetching workspaces: {workspaces_response['error']}"
    
    for workspace in workspaces_response:
        if workspace.get("name") == workspaces_response:
            return workspace.get("id")
    
    return f"Workspace with name '{workspaces_response}' doesn't exist"

########################
# Resources
########################

@mcp.resource("toggl:://entities/{workspace_id}/projects")
async def _get_projects(workspace_id: int) -> dict:
    """
    Retrieve a full list of all projects within the user's Toggl workspace, including detailed metadata for each project.

    This resource exposes rich, structured project information that can be used by LLMs or clients for:
    
    - Identifying project names and corresponding IDs for use in tool calls (e.g., creating or tagging time entries)
    - Reasoning over project metadata such as billing status, creation date, and activity status
    - Filtering or grouping projects by properties like `status`, `is_private`, `pinned`, or `can_track_time`
    - Auditing recent or upcoming projects via timestamps such as `created_at` or `start_date`

    Returned Schema
    The response includes a `projects` key containing a list of objects, each with fields like:

    - `id`: Unique Toggl project ID
    - `name`: Human-readable name of the project
    - `workspace_id`: ID of the workspace this project belongs to
    - `is_private`: Whether the project is private to the creator
    - `active`: Boolean flag indicating if the project is currently active
    - `created_at`: Timestamp of when the project was created
    - `status`: Project status (e.g., "upcoming", "active", etc.)
    - `billable`: Whether time tracked to the project is billable
    - `pinned`: Whether the project is pinned in the UI
    - `color`: Hex code representing the UI display color of the project
    - `client_name`: Name of the client associated with the project (if any)
    - `estimated_hours`: Estimated hours (if set)
    - `can_track_time`: Whether time can currently be tracked against this project
    """
    url = f"https://api.track.toggl.com/api/v9/workspaces/{workspace_id}/projects"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return {"projects": response.json()}
        except Exception as e:
            return {"error": e}

@mcp.resource("toggl:://me/time_entries")
async def _get_time_entries() -> dict:
    """
    Retrieve all time entries associated with the authenticated Toggl user.

    This MCP resource exposes raw time entry data for the authenticated user, including active and recently completed sessions. It enables language models to reason over existing tracked sessions, summarize activity, or link time entries to projects or tags.
    """
    url = "https://api.track.toggl.com/api/v9/me/time_entries"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                return {"error" : "User does not have access to this resource"}
            elif e.response.status_code == 500:
                return {"error" : "Internal Server Error"}
            else:
                return {"error": f"Unknown Error Code: {e.response.status_code}"}
        except Exception as e:
            return {"error": e}

@mcp.resource("toggl:://me/workspaces")
async def _get_workspaces() -> dict:
    """
    Retrieve all workspaces associated with the authenticated Toggl user.
    """
    url = "https://api.track.toggl.com/api/v9/me/workspaces"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                return {"error" : "User does not have access to this resource"}
            elif e.response.status_code == 500:
                return {"error" : "Internal Server Error"}
            else:
                return {"error": f"Unknown Error Code: {e.response.status_code}"}
        except Exception as e:
            return {"error": e}


########################
# Tools
########################

##########################
# Tools for Projects
##########################

@mcp.tool()
async def create_project(
    name: str,
    workspace_name: Optional[str] = None,
    active: Optional[bool] = True,
    billable: Optional[bool] = False,
    client_id: Optional[int] = None,
    color: Optional[TOGGL_COLORS] = None,
    is_private: Optional[bool] = True,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    estimated_hours: Optional[int] = None,
    template: Optional[bool] = False,
    template_id: Optional[int] = None
) -> Union[dict, str]:
    """
    Creates a new project in a Toggl workspace.

    If `workspace_name` is not provided, set it as None.

    If color is not in TOGGL_COLORS, choose color from TOGGL_COLORS which is
    most similar to the given color.

    Args:
        name (str): Name of the project to create
        workspace_name (str, optional): Name of the workspace. Defaults to user's default workspace.
        active (bool, optional): Whether project is active. Defaults to True
        billable (bool, optional): Whether project is billable. Defaults to False
        client_id (int, optional): Associated client ID
        color (str, optional): Project color hex code. Must be one of:
            - "#4dc3ff" (Light Blue)
            - "#bc85e6" (Lavender)
            - "#df7baa" (Pink)
            - "#f68d38" (Orange)
            - "#b27636" (Brown)
            - "#8ab734" (Lime Green)
            - "#14a88e" (Teal)
            - "#268bb5" (Medium Blue)
            - "#6668b4" (Purple)
            - "#a4506c" (Rose)
            - "#67412c" (Dark Brown)
            - "#3c6526" (Forest Green)
            - "#094558" (Navy Blue)
            - "#bc2d07" (Red)
            - "#999999" (Gray)
        is_private (bool, optional): Whether project is private. Defaults to True
        start_date (str, optional): Project start date in ISO format
        end_date (str, optional): Project end date in ISO format
        estimated_hours (int, optional): Estimated project hours
        template (bool, optional): Whether this is a template. Defaults to False
        template_id (int, optional): ID of template to use

    Returns:
        dict: Project data on success
        str: Error message on failure
    """
    if workspace_name is None:
        workspace_id = await _get_default_workspace_id()
    else:
        workspace_id = await _get_workspace_id_by_name(workspace_name)

    if isinstance(workspace_id, str):  # Error message
        return workspace_id

    response = await _create_project_helper(
        name=name,
        workspace_id=workspace_id,
        active=active,
        billable=billable,
        client_id=client_id,
        color=color,
        is_private=is_private,
        start_date=start_date,
        end_date=end_date,
        estimated_hours=estimated_hours,
        template=template,
        template_id=template_id
    )

    if isinstance(response, str):  # Error message
        return f"Failed to create project: {response}"
    
    return response

@mcp.tool()
async def delete_project(project_name: str, workspace_name: Optional[str] = None) -> str:
    """
    Deletes a Toggl project by its name.

    If `workspace_name` is not provided, set it as None.

        Args:
        project_name (str): The name of the project to delete.
        workspace_name (str, optional): Name of the Toggl workspace. If not provided, defaults to the user's default workspace.

    Returns:
        str: Success message if the project is deleted, or an error message if it fails.
    """
    if workspace_name is None:
        workspace_id = await _get_default_workspace_id()
    else:
        workspace_id = await _get_workspace_id_by_name(workspace_name)

    if isinstance(workspace_id, str):  # Error message
        return workspace_id

    project_id = await _get_project_id_by_name(project_name, workspace_id)
    
    if isinstance(project_id, str):  # Error message
        return project_id
    
    delete_status = await _delete_project_helper(project_id, workspace_id)

    if isinstance(delete_status, int):
        return f"Successfully deleted the project with project_id: {project_id}"
    elif isinstance(delete_status, str) and delete_status == "Project not found/accessible":
        return f"Project with project_id {project_id} was not found or is inaccessible."
    else:
        return f"Failed to delete project {project_id}. Details: {delete_status}"

@mcp.tool()
async def update_projects(
    project_names: List[str],
    workspace_name: Optional[str] = None,
    operations: Optional[List[Any]] = None
) -> Union[dict, str]:
    """
    Update multiple projects in bulk using PATCH operations.

    If `workspace_name` is not provided, set it as None.

    Args:
        project_names (List[str]): List of project names to update
        workspace_name (str, optional): Name of the workspace. Defaults to user's default workspace.
        operations (List[Any], optional): List of patch operations, each containing:
            - op (str): Operation type ("add", "remove", "replace") 
            - path (str): Path to field (e.g., "/color")
            - value (Any): New value for the field

    Returns:
        dict: Response containing success/failure info for each project
        str: Error message if the operation fails`
    """
    if operations is None:
        return "Error: No operations provided for update."

    if workspace_name is None:
        workspace_id = await _get_default_workspace_id() 
    else:
        workspace_id = await _get_workspace_id_by_name(workspace_name)

    if isinstance(workspace_id, str):  # Error message
        return workspace_id


    project_ids = []
    for name in project_names:
        project_id = await _get_project_id_by_name(name, workspace_id)
        if isinstance(project_id, str):  # Error message
            return f"Error with project '{name}': {project_id}"
        project_ids.append(project_id)

    response = await _update_projects_helper(
        workspace_id=workspace_id,
        project_ids=project_ids,
        operations=operations
    )

    if isinstance(response, str):
        return f"Failed to update projects: {response}"
        
    return response

@mcp.tool()
async def get_all_projects(workspace_name: Optional[str] = None) -> Union[dict, str]:
    """
    Retrieve all projects in the user's Toggl workspace.

    If `workspace_name` is not provided, the default workspace will be used.

    Args:
        workspace_name (str, optional): Name of the workspace to fetch projects from.
                                        Defaults to the user's default workspace if None.
    Returns:
        dict: JSON response containing all projects in the user's workspace.
        str: Error message if the request fails.
    """
    if workspace_name is None:
        workspace_id = await _get_default_workspace_id()
        if isinstance(workspace_id, str): 
             return f"Error fetching default workspace ID: {workspace_id}"
        if workspace_id is None: 
             return "Error: Could not determine default workspace ID."
    else:
        workspace_id = await _get_workspace_id_by_name(workspace_name)

    if isinstance(workspace_id, str):
        return workspace_id 

    projects_response = await _get_projects(workspace_id)

    if isinstance(projects_response, dict) and "error" in projects_response:
        return f"Error fetching projects for workspace ID {workspace_id}: {projects_response['error']}"
    elif not isinstance(projects_response, dict) or "projects" not in projects_response:
         return f"Error: Unexpected response format when fetching projects for workspace ID {workspace_id}."

    return projects_response


#########################
# Tools for Time Entries
#########################


@mcp.tool()
async def new_time_entry(
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    project_name: Optional[str] = None,
    start: Optional[str] = None,
    stop: Optional[str] = None,
    duration: Optional[int] = -1,
    billable: Optional[bool] = False,
    workspace_name: Optional[str] = None
) -> dict:
    """
    Create a Toggl Track time entry with flexible options for live or past tracking.

    If `workspace_name` is not provided, set it as None.

    Duration is in seconds. Set to -1 for live tracking for the current time entry.
    
    Use this tool to start a new entry (live tracking) or log a completed activity with precise timing.

    Examples:
    - "Track 'Writing docs' starting now"
    - "Log 2 hours spent on 'MCP Server' yesterday tagged ['Toggl', 'backend']"

    Args:
        description (str, optional): What the time entry is about.
        tags (List[str], optional): List of tags (names only).
        project_name (str, optional): Name of the associated project.
        start (str, optional): ISO 8601 UTC start time.
        stop (str, optional): ISO 8601 UTC stop time.
        duration (int, optional): Duration in seconds. Set to -1 for live tracking.
        billable (bool, optional): Whether this is billable time.
        workspace_name (str, optional): Name of the workspace. Defaults to user's default workspace if omitted.

    Returns:
        dict: Toggl API response on success.
        dict: Error message on failure.
    """
    if workspace_name is None:
        workspace_id = await _get_default_workspace_id()
    else:
        workspace_id = await _get_workspace_id_by_name(workspace_name)

    if isinstance(workspace_id, str):
        return {"error": workspace_id}
    if workspace_id is None: 
        return {"error": "Could not determine workspace ID."}

    project_id = None 
    if project_name is not None:
        project_id_or_error = await _get_project_id_by_name(project_name, workspace_id)
        if isinstance(project_id_or_error, str):
            return {"error": project_id_or_error}
        else:
            project_id = project_id_or_error

    final_start_for_api = start # Default to original values
    final_stop_for_api = stop
    debug_info = {
        "correction_applied_start": False, "original_start_input": start,
        "correction_applied_stop": False, "original_stop_input": stop,
        "system_timezone": None
    }
    local_tz = None # Define here to potentially reuse

    # Correct START time
    if start:
        try:
            naive_time_str = start.split('.')[0].replace('Z', '')
            assumed_local_naive_dt = datetime.datetime.fromisoformat(naive_time_str)
            if local_tz is None:
                 local_tz = get_localzone()
                 if not local_tz: raise ValueError("Failed to get local timezone")
                 debug_info["system_timezone"] = getattr(local_tz, 'key', str(local_tz))

            if hasattr(local_tz, 'localize'): assumed_local_dt = local_tz.localize(assumed_local_naive_dt, is_dst=None)
            elif hasattr(assumed_local_naive_dt, 'replace'): assumed_local_dt = assumed_local_naive_dt.replace(tzinfo=local_tz)
            else: raise TypeError("Unsupported timezone object from get_localzone()")

            corrected_utc_dt = assumed_local_dt.astimezone(timezone.utc)
            final_start_for_api = _iso_timestamp(corrected_utc_dt)
            # --- V V V FIXED DEBUG KEY V V V ---
            debug_info["correction_applied_start"] = True # Correct key
            # --- ^ ^ ^ FIXED DEBUG KEY ^ ^ ^ ---
            debug_info["corrected_utc_start"] = final_start_for_api

        except Exception as e:
            print(f"WARNING: Timezone correction failed for start='{start}': {e}. Using original value.")
            final_start_for_api = start
            debug_info["correction_error_start"] = str(e)
            debug_info["correction_applied_start"] = False # Ensure it's false on error

    # Correct STOP time
    if stop:
        try:
            naive_time_str = stop.split('.')[0].replace('Z', '')
            assumed_local_naive_dt = datetime.datetime.fromisoformat(naive_time_str)
            if local_tz is None: # Get timezone only if needed
                 local_tz = get_localzone()
                 if not local_tz: raise ValueError("Failed to get local timezone")
                 # Update debug info only if fetched here
                 if debug_info["system_timezone"] is None:
                     debug_info["system_timezone"] = getattr(local_tz, 'key', str(local_tz))

            if hasattr(local_tz, 'localize'): assumed_local_dt = local_tz.localize(assumed_local_naive_dt, is_dst=None)
            elif hasattr(assumed_local_naive_dt, 'replace'): assumed_local_dt = assumed_local_naive_dt.replace(tzinfo=local_tz)
            else: raise TypeError("Unsupported timezone object from get_localzone()")

            corrected_utc_dt = assumed_local_dt.astimezone(timezone.utc)
            final_stop_for_api = _iso_timestamp(corrected_utc_dt)
            debug_info["correction_applied_stop"] = True # Correct key
            debug_info["corrected_utc_stop"] = final_stop_for_api

        except Exception as e:
            print(f"WARNING: Timezone correction failed for stop='{stop}': {e}. Using original value.")
            final_stop_for_api = stop
            debug_info["correction_error_stop"] = str(e)
            debug_info["correction_applied_stop"] = False # Ensure it's false on error

    # --- Call Helper ---
    # REMINDER: Ensure _new_time_entry_helper handles parameter conflicts (start/stop/duration)
    toggl_time_entry = await _new_time_entry_helper(
        description=description,
        tags=tags,
        project_id=project_id,
        start=final_start_for_api,
        stop=final_stop_for_api,
        duration=duration if start else -1, # Pass original duration
        billable=billable,
        workspace_id=workspace_id
    )

    # --- Handle Response ---
    if isinstance(toggl_time_entry, str) and toggl_time_entry.startswith("Error:"):
        return {"error": toggl_time_entry, "debug_info": debug_info}
    if not isinstance(toggl_time_entry, tuple) or len(toggl_time_entry) != 2:
         return {"error": f"Unexpected response format from _new_time_entry_helper: {toggl_time_entry}", "debug_info": debug_info}

    toggl_time_entry_response, api_call_local_time = toggl_time_entry

    debug_info["final_start_passed_to_helper"] = final_start_for_api
    debug_info["final_stop_passed_to_helper"] = final_stop_for_api

    return {
        "toggle_time_entry_response": toggl_time_entry_response,
        "api_call_local_time": api_call_local_time,
        "debug_info": debug_info
    }

@mcp.tool()
async def stopping_time_entry(time_entry_name: str, workspace_name: Optional[str] = None) -> Union[dict, str]:
    """
    Stop a currently running time entry by name.

    This function looks up the time entry by its description, retrieves its ID, and then calls the Toggl API to stop it.

    If `workspace_name` is not provided, set it as None.

    Args:
        time_entry_name (str): Description of the currently running time entry to stop.
        workspace_name (str, optional): Name of the workspace. Defaults to the user's default workspace.

    Returns:
        dict: JSON response from the Toggl API if successful.
        str: An error message if the request fails or no matching time entry is found.
    """
    if workspace_name is None:
        workspace_id = await _get_default_workspace_id()
    else:
        workspace_id = await _get_workspace_id_by_name(workspace_name)

    if isinstance(workspace_id, str):  # Error message
        return workspace_id
    
    time_entry_id = await _get_time_entry_id_by_name(time_entry_name, workspace_id)

    if isinstance(time_entry_id, str): # Error message
        return time_entry_id

    stopping_time_entry_response = await _stopping_time_entry_helper(time_entry_id, workspace_id)

    if isinstance(stopping_time_entry_response, str) and stopping_time_entry_response == "Time entry not found":
        return "Time entry not found!"
    elif isinstance(stopping_time_entry_response, dict):
        return stopping_time_entry_response 
    else:
        return "ERROR"

@mcp.tool()
async def delete_time_entry(time_entry_name: str, workspace_name: Optional[str]=None) -> str:
    """
    Deletes a time entry by its description.

    This permanently removes the time entry from the workspace, so use with caution.

    If `workspace_name` is not provided, set it as None.

    Args:
        time_entry_name (str): Description of the time entry to delete.
        workspace_name (str, optional): Name of the workspace. Defaults to the user's default workspace.

    Returns:
        str: A success message if deleted, or an error string if it fails.
    """
    if workspace_name is None:
        workspace_id = await _get_default_workspace_id()
    else:
        workspace_id = await _get_workspace_id_by_name(workspace_name)

    if isinstance(workspace_id, str):  # Error message
        return workspace_id

    time_entry_id = await _get_time_entry_id_by_name(time_entry_name, workspace_id)
    
    if isinstance(time_entry_id, str):  # Error message
        return time_entry_id
    
    delete_status = await _deleting_time_entry_helper(time_entry_id, workspace_id)

    if isinstance(delete_status, int):
        return f"Successfully deleted the time entry with time_entry_id: {time_entry_id}"
    elif isinstance(delete_status, str) and delete_status == "Time Entry not found/accessible":
        return f"Time entry with time_entry_id {time_entry_id} was not found or is inaccessible."
    else:
        return f"Failed to delete time_entry {time_entry_id}. Details: {delete_status}"

@mcp.tool()
async def get_current_time_entry() -> Union[dict, str]:
    """
    Fetch the currently running time entry for the authenticated Toggl user.

    This helper function queries the Toggl Track API for the active (i.e., currently ongoing) time entry associated with the authenticated user.
    It is useful for determining what the user is currently working on, displaying real-time status, or stopping/modifying the active session.

    Args:
    - None.

    Returns:
    - `dict`: JSON object describing the currently running time entry, or containing `data: None` if none is active.
    - `str`: Descriptive error message if the request fails due to authorization, connectivity, or internal server errors.
    """
    current_time_entry_data = await _get_current_time_entry_helper()

    if isinstance(current_time_entry_data, str):
        return current_time_entry_data

    return current_time_entry_data

@mcp.tool()
async def updating_time_entry(time_entry_name: str, 
                            workspace_name: Optional[str]=None,
                            description: Optional[str] = None,
                            tags: Optional[List[str]] = None, 
                            project_id: Optional[int] = None, 
                            start: Optional[str] = None, 
                            stop: Optional[str] = None,  
                            duration: Optional[int] = None,
                            billable: Optional[bool] = None) -> Union[dict, str]:
        """
        Update one or more attributes of an existing time entry in the Toggl Track workspace.

        If `workspace_name` is not provided, set it as None.

        Args:
            time_entry_name (str): Description of the time entry to update.
            workspace_name (str, optional): Name of the workspace. Defaults to the user's default.
            description (str, optional): New description.
            tags (List[str], optional): New list of tags.
            project_id (int, optional): New project ID.
            start (str, optional): New start timestamp (ISO 8601).
            stop (str, optional): New stop timestamp.
            duration (int, optional): Duration in seconds.
            billable (bool, optional): Whether the entry is billable.

        Returns:
            dict: JSON response from Toggl if update is successful.
            str: Error message on failure.
        """
        if workspace_name is None:
            workspace_id = await _get_default_workspace_id()
        else:
            workspace_id = await _get_workspace_id_by_name(workspace_name)

        if isinstance(workspace_id, str):  # Error message
            return workspace_id
        
        time_entry_id = await _get_time_entry_id_by_name(time_entry_name, workspace_id)
        
        if isinstance(time_entry_id, str):  # Error message
            return time_entry_id

        response = await _update_time_entry_helper(time_entry_id=time_entry_id,
            workspace_id=workspace_id,
            description=description,
            tags=tags,
            project_id=project_id,
            start=start,
            stop=stop,
            duration=duration,
            billable=billable
        )

        return response

@mcp.tool()
async def get_time_entries_for_range(
    from_day_offset: Optional[int] = 0,
    to_day_offset: Optional[int] = 0,
) -> Union[List[dict], str]:
    """
    Retrieves time entries for the authenticated Toggl user within a specific UTC day range.

    This tool allows you to query all entries from a specific day or over multiple days,
    using day offsets from today.

    Examples:
    - To get entries for today: `from_day_offset=0`, `to_day_offset=0`
    - For yesterday only: `from_day_offset=-1`, `to_day_offset=-1`
    - For the last two days: `from_day_offset=-1`, `to_day_offset=0`

    Args:
        from_day_offset (int, optional): Days offset before today for the start of the range. Defaults to 0 (today).
        to_day_offset (int, optional): Days offset before today for the end of the range. Defaults to 0 (today).

    Returns:
        List[dict]: Filtered time entries that fall within the given date range.
        str: Error message if retrieval or filtering fails.
    """
    from_day_offset = from_day_offset if from_day_offset is not None else 0
    to_day_offset = to_day_offset if to_day_offset is not None else 0

    all_entries = await _get_time_entries()

    if isinstance(all_entries, dict) and "error" in all_entries:
        return f"Failed to retrieve entries: {all_entries['error']}"

    start_time, _ = _get_date_range(from_day_offset)
    _, end_time = _get_date_range(to_day_offset)

    def _in_range(entry: dict) -> bool:
        entry_start = entry.get("start")
        if entry_start is None:
            return False 
        return start_time <= entry_start <= end_time

    filtered = [entry for entry in all_entries if _in_range(entry)]
    return filtered

if __name__ == "__main__":
    mcp.run()