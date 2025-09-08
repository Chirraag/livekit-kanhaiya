import logging
from livekit.agents import function_tool, RunContext, get_job_context
from livekit import api
import requests
from langchain_community.tools import DuckDuckGoSearchRun
import os
import json
from typing import Optional, List, Dict, Any


@function_tool()
async def get_weather(
    context: RunContext,  # type: ignore
    city: str) -> str:
    """
    Get the current weather for a given city.
    """
    try:
        response = requests.get(
            f"https://wttr.in/{city}?format=3")
        if response.status_code == 200:
            logging.info(f"Weather for {city}: {response.text.strip()}")
            return response.text.strip()   
        else:
            logging.error(f"Failed to get weather for {city}: {response.status_code}")
            return f"Could not retrieve weather for {city}."
    except Exception as e:
        logging.error(f"Error retrieving weather for {city}: {e}")
        return f"An error occurred while retrieving weather for {city}." 

@function_tool()
async def search_web(
    context: RunContext,  # type: ignore
    query: str) -> str:
    """
    Search the web using DuckDuckGo.
    """
    logging.info(f"🔧 Tool 'search_web' invoked with parameters: {{'query': '{query}'}}")
    logging.info(f"📡 Making web search request via DuckDuckGo")
    
    try:
        results = DuckDuckGoSearchRun().run(tool_input=query)
        logging.info(f"✅ Tool 'search_web' completed successfully")
        logging.info(f"📝 Tool 'search_web' response: {results[:500]}{'...' if len(results) > 500 else ''}")
        return results
    except Exception as e:
        error_msg = f"An error occurred while searching the web for '{query}'."
        logging.error(f"❌ Tool 'search_web' exception: {e}")
        return error_msg

@function_tool()
async def end_call(
    context: RunContext,  # type: ignore
    reason: str = "Call completed"
) -> str:
    """
    End the current call/session. Use when conversation is complete or user requests to hang up.
    """
    logging.info(f"🔧 Tool 'end_call' invoked with reason: '{reason}'")
    logging.info(f"📞 Initiating call termination")
    
    try:
        # Say goodbye first
        await context.session.generate_reply(
            instructions=f"Say a polite goodbye. Reason: {reason}. Do NOT mention function names or special characters."
        )
        
        logging.info(f"🔌 Deleting room to end call...")
        
        # Get job context and delete room (this ends the call)
        job_ctx = get_job_context()
        await job_ctx.api.room.delete_room(
            api.DeleteRoomRequest(room=job_ctx.room.name)
        )
        
        logging.info(f"✅ Call ended successfully: {reason}")
        return f"Call ended: {reason}. Goodbye!"
        
    except Exception as e:
        # Handle specific "room not found" error as success (room already deleted)
        if "requested room does not exist" in str(e) or "not_found" in str(e):
            logging.info(f"✅ Call ended successfully: {reason} (room already deleted)")
            return f"Call ended: {reason}. Goodbye!"
        else:
            logging.error(f"❌ Error ending call: {e}")
            return f"Error ending call: {str(e)}"


@function_tool()    
async def send_email(
    context: RunContext,  # type: ignore
    to_email: str,
    subject: str,
    message: str,
    cc_email: Optional[str] = None
) -> str:
    """
    Send an email through Gmail.
    
    Args:
        to_email: Recipient email address
        subject: Email subject line
        message: Email body content
        cc_email: Optional CC email address
    """
    try:
        # Gmail SMTP configuration
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        
        # Get credentials from environment variables
        gmail_user = os.getenv("GMAIL_USER")
        gmail_password = os.getenv("GMAIL_APP_PASSWORD")  # Use App Password, not regular password
        
        if not gmail_user or not gmail_password:
            logging.error("Gmail credentials not found in environment variables")
            return "Email sending failed: Gmail credentials not configured."
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = gmail_user
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Add CC if provided
        recipients = [to_email]
        if cc_email:
            msg['Cc'] = cc_email
            recipients.append(cc_email)
        
        # Attach message body
        msg.attach(MIMEText(message, 'plain'))
        
        # Connect to Gmail SMTP server
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Enable TLS encryption
        server.login(gmail_user, gmail_password)
        
        # Send email
        text = msg.as_string()
        server.sendmail(gmail_user, recipients, text)
        server.quit()
        
        logging.info(f"Email sent successfully to {to_email}")
        return f"Email sent successfully to {to_email}"
        
    except smtplib.SMTPAuthenticationError:
        logging.error("Gmail authentication failed")
        return "Email sending failed: Authentication error. Please check your Gmail credentials."
    except smtplib.SMTPException as e:
        logging.error(f"SMTP error occurred: {e}")
        return f"Email sending failed: SMTP error - {str(e)}"
    except Exception as e:
        logging.error(f"Error sending email: {e}")
        return f"An error occurred while sending email: {str(e)}"

def create_dynamic_tool(tool_config: Dict[str, Any]):
    """Create a dynamic tool function based on configuration"""
    tool_name = tool_config['name']
    description = tool_config['description']
    request_type = tool_config['requestType']
    request_url = tool_config['requestUrl']
    parameters = tool_config.get('parameters', [])
    
    # For simplicity, create a basic tool that handles common parameter patterns
    # This avoids the **kwargs issue with the LiveKit framework
    
    if len(parameters) == 0:
        # No parameters tool - create unique function per tool
        async def tool_function(context: RunContext) -> str:
            """Execute HTTP request with no parameters"""
            logging.info(f"🔧 Tool '{tool_name}' invoked with no parameters")
            logging.info(f"📡 Making {request_type} request to: {request_url}")
            
            try:
                if request_type.upper() == 'GET':
                    response = requests.get(request_url)
                elif request_type.upper() == 'POST':
                    response = requests.post(request_url)
                elif request_type.upper() == 'PUT':
                    response = requests.put(request_url)
                elif request_type.upper() == 'DELETE':
                    response = requests.delete(request_url)
                else:
                    error_msg = f"Unsupported request type: {request_type}"
                    logging.error(f"❌ Tool '{tool_name}' failed: {error_msg}")
                    return error_msg
                
                logging.info(f"📊 Tool '{tool_name}' received HTTP {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        result = response.json()
                        result_str = json.dumps(result, indent=2)
                        logging.info(f"✅ Tool '{tool_name}' completed successfully")
                        logging.info(f"📝 Tool '{tool_name}' response: {result_str[:500]}{'...' if len(result_str) > 500 else ''}")
                        return result_str
                    except:
                        logging.info(f"✅ Tool '{tool_name}' completed successfully")
                        logging.info(f"📝 Tool '{tool_name}' response: {response.text[:500]}{'...' if len(response.text) > 500 else ''}")
                        return response.text
                else:
                    error_msg = f"Error: HTTP {response.status_code} - {response.text}"
                    logging.error(f"❌ Tool '{tool_name}' failed: HTTP {response.status_code} - {response.text}")
                    return error_msg
                    
            except Exception as e:
                error_msg = f"An error occurred while using {tool_name}: {str(e)}"
                logging.error(f"❌ Tool '{tool_name}' exception: {e}")
                return error_msg
        
        # Set function metadata before decorating
        tool_function.__name__ = tool_name
        tool_function.__doc__ = description
        # Return decorated function
        return function_tool()(tool_function)
    
    elif len(parameters) == 1:
        # Single parameter tool
        param = parameters[0]
        param_name = param['name']
        param_required = param.get('required', False)
        param_default = param.get('defaultValue', '')
        
        if param_required:
            async def tool_function(context: RunContext, param_value: str) -> str:
                """Execute HTTP request with one parameter"""
                data = {param_name: param_value}
                logging.info(f"🔧 Tool '{tool_name}' invoked with parameters: {data}")
                logging.info(f"📡 Making {request_type} request to: {request_url}")
                
                try:
                    if request_type.upper() == 'GET':
                        response = requests.get(request_url, params=data)
                    elif request_type.upper() == 'POST':
                        response = requests.post(request_url, json=data)
                    elif request_type.upper() == 'PUT':
                        response = requests.put(request_url, json=data)
                    elif request_type.upper() == 'DELETE':
                        response = requests.delete(request_url, params=data)
                    else:
                        error_msg = f"Unsupported request type: {request_type}"
                        logging.error(f"❌ Tool '{tool_name}' failed: {error_msg}")
                        return error_msg
                    
                    logging.info(f"📊 Tool '{tool_name}' received HTTP {response.status_code}")
                    
                    if response.status_code == 200:
                        try:
                            result = response.json()
                            result_str = json.dumps(result, indent=2)
                            logging.info(f"✅ Tool '{tool_name}' completed successfully")
                            logging.info(f"📝 Tool '{tool_name}' response: {result_str[:500]}{'...' if len(result_str) > 500 else ''}")
                            return result_str
                        except:
                            logging.info(f"✅ Tool '{tool_name}' completed successfully")
                            logging.info(f"📝 Tool '{tool_name}' response: {response.text[:500]}{'...' if len(response.text) > 500 else ''}")
                            return response.text
                    else:
                        error_msg = f"Error: HTTP {response.status_code} - {response.text}"
                        logging.error(f"❌ Tool '{tool_name}' failed: HTTP {response.status_code} - {response.text}")
                        return error_msg
                        
                except Exception as e:
                    error_msg = f"An error occurred while using {tool_name}: {str(e)}"
                    logging.error(f"❌ Tool '{tool_name}' exception: {e}")
                    return error_msg
            
            # Set function name and return decorated function
            tool_function.__name__ = tool_name
            tool_function.__doc__ = description
            return function_tool()(tool_function)
            
        else:
            async def tool_function(context: RunContext, param_value: str = param_default) -> str:
                """Execute HTTP request with one optional parameter"""
                data = {param_name: param_value}
                logging.info(f"🔧 Tool '{tool_name}' invoked with parameters: {data}")
                logging.info(f"📡 Making {request_type} request to: {request_url}")
                
                try:
                    if request_type.upper() == 'GET':
                        response = requests.get(request_url, params=data)
                    elif request_type.upper() == 'POST':
                        response = requests.post(request_url, json=data)
                    elif request_type.upper() == 'PUT':
                        response = requests.put(request_url, json=data)
                    elif request_type.upper() == 'DELETE':
                        response = requests.delete(request_url, params=data)
                    else:
                        error_msg = f"Unsupported request type: {request_type}"
                        logging.error(f"❌ Tool '{tool_name}' failed: {error_msg}")
                        return error_msg
                    
                    logging.info(f"📊 Tool '{tool_name}' received HTTP {response.status_code}")
                    
                    if response.status_code == 200:
                        try:
                            result = response.json()
                            result_str = json.dumps(result, indent=2)
                            logging.info(f"✅ Tool '{tool_name}' completed successfully")
                            logging.info(f"📝 Tool '{tool_name}' response: {result_str[:500]}{'...' if len(result_str) > 500 else ''}")
                            return result_str
                        except:
                            logging.info(f"✅ Tool '{tool_name}' completed successfully")
                            logging.info(f"📝 Tool '{tool_name}' response: {response.text[:500]}{'...' if len(response.text) > 500 else ''}")
                            return response.text
                    else:
                        error_msg = f"Error: HTTP {response.status_code} - {response.text}"
                        logging.error(f"❌ Tool '{tool_name}' failed: HTTP {response.status_code} - {response.text}")
                        return error_msg
                        
                except Exception as e:
                    error_msg = f"An error occurred while using {tool_name}: {str(e)}"
                    logging.error(f"❌ Tool '{tool_name}' exception: {e}")
                    return error_msg
            
            # Set function name and return decorated function
            tool_function.__name__ = tool_name
            tool_function.__doc__ = description
            return function_tool()(tool_function)
    
    else:
        # Multiple parameters - for now, skip complex tools to avoid type issues
        logging.warning(f"Skipping tool {tool_name} with multiple parameters - not yet supported")
        return None

def get_dynamic_tools(tools_config: List[Dict[str, Any]]) -> List:
    """Generate dynamic tools based on configuration"""
    dynamic_tools = []
    
    for tool_config in tools_config:
        if not tool_config.get('enabled', True):
            continue
            
        tool_name = tool_config.get('name', '')
        
        # Handle built-in tools
        if tool_name == 'search_web':
            dynamic_tools.append(search_web)
        elif tool_name == 'end_call':
            dynamic_tools.append(end_call)
        else:
            # Create dynamic tool for other tools
            if tool_name and tool_config.get('requestUrl'):
                try:
                    dynamic_tool = create_dynamic_tool(tool_config)
                    if dynamic_tool is not None:
                        dynamic_tools.append(dynamic_tool)
                except Exception as e:
                    logging.error(f"Failed to create dynamic tool {tool_name}: {e}")
    
    # No fallback - only include tools that are explicitly enabled in configuration
    
    return dynamic_tools