import logging
from livekit.agents import function_tool, RunContext, get_job_context
from livekit import api
import requests
from langchain_community.tools import DuckDuckGoSearchRun
import os
import json
from typing import Optional, List, Dict, Any
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


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
        
        # Get job context
        job_ctx = get_job_context()
        
        logging.info(f"🔌 Disconnecting agent from room...")
        
        # Disconnect the agent from the room
        await job_ctx.shutdown()
        
        logging.info(f"✅ Call ended successfully: {reason}")
        return f"Call ended: {reason}. Goodbye!"
        
    except Exception as e:
        logging.error(f"❌ Error ending call: {e}")
        # Even if there's an error, try to shutdown
        try:
            job_ctx = get_job_context()
            await job_ctx.shutdown()
            logging.info(f"✅ Call ended successfully: {reason} (after error recovery)")
            return f"Call ended: {reason}. Goodbye!"
        except:
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
        gmail_user = "kanhaiya@vexalink.com"
        gmail_password = "kobbpztdcgymkefw"  # Use App Password, not regular password
        
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

def build_tool_docstring(description: str, parameters: List[Dict[str, Any]]) -> str:
    """Build a comprehensive docstring for the tool function"""
    if not parameters:
        return description
    
    # Build parameter documentation
    param_docs = []
    for param in parameters:
        param_name = param['name']
        param_desc = param.get('description', f'The {param_name} parameter')
        param_required = param.get('required', False)
        param_default = param.get('defaultValue', '')
        
        if param_required:
            param_docs.append(f"    {param_name}: {param_desc}")
        else:
            param_docs.append(f"    {param_name}: {param_desc} (optional, default: '{param_default}')")
    
    # Build complete docstring
    docstring = f"""{description}
    
    Args:
{chr(10).join(param_docs)}
    
    Returns:
        str: API response in JSON format
    """
    
    return docstring

def create_dynamic_tool(tool_config: Dict[str, Any]):
    """Create a dynamic tool function based on configuration"""
    tool_name = tool_config['name']
    description = tool_config['description']
    request_type = tool_config['requestType']
    request_url = tool_config['requestUrl']
    parameters = tool_config.get('parameters', [])
    
    # For simplicity, create a basic tool that handles common parameter patterns
    # This avoids the **kwargs issue with the LiveKit framework
    
    # Build comprehensive docstring with parameter descriptions
    tool_docstring = build_tool_docstring(description, parameters)
    
    if len(parameters) == 0:
        # No parameters tool - create unique function per tool
        async def tool_function(context: RunContext) -> str:
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
        tool_function.__doc__ = tool_docstring
        # Return decorated function
        return function_tool()(tool_function)
    
    elif len(parameters) == 1:
        # Single parameter tool
        param = parameters[0]
        param_name = param['name']
        param_desc = param.get('description', f'The {param_name} parameter')
        param_required = param.get('required', False)
        param_default = param.get('defaultValue', '')
        
        if param_required:
            async def tool_function(context: RunContext, param_value: str) -> str:
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
            tool_function.__doc__ = tool_docstring
            return function_tool()(tool_function)
            
        else:
            async def tool_function(context: RunContext, param_value: str = param_default) -> str:
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
            tool_function.__doc__ = tool_docstring
            return function_tool()(tool_function)
    
    elif len(parameters) == 2:
        # Two parameters tool
        param1 = parameters[0]
        param2 = parameters[1]
        param1_name = param1['name']
        param2_name = param2['name']
        param1_desc = param1.get('description', f'The {param1_name} parameter')
        param2_desc = param2.get('description', f'The {param2_name} parameter')
        param1_required = param1.get('required', False)
        param2_required = param2.get('required', False)
        param1_default = param1.get('defaultValue', '')
        param2_default = param2.get('defaultValue', '')
        
        if param1_required and param2_required:
            async def tool_function(context: RunContext, param1_value: str, param2_value: str) -> str:
                data = {param1_name: param1_value, param2_name: param2_value}
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
            
            # Set function metadata
            tool_function.__name__ = tool_name
            tool_function.__doc__ = tool_docstring
            # Dynamically set parameter names in function signature
            tool_function.__code__ = tool_function.__code__.replace(
                co_varnames=('context', param1_name, param2_name)
            ) if hasattr(tool_function.__code__, 'replace') else tool_function.__code__
            return function_tool()(tool_function)
            
        elif param1_required and not param2_required:
            async def tool_function(context: RunContext, param1_value: str, param2_value: str = param2_default) -> str:
                data = {param1_name: param1_value, param2_name: param2_value}
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
            
            # Set function metadata
            tool_function.__name__ = tool_name
            tool_function.__doc__ = tool_docstring
            return function_tool()(tool_function)
            
        else:
            async def tool_function(context: RunContext, param1_value: str = param1_default, param2_value: str = param2_default) -> str:
                data = {param1_name: param1_value, param2_name: param2_value}
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
            
            # Set function metadata
            tool_function.__name__ = tool_name
            tool_function.__doc__ = tool_docstring
            return function_tool()(tool_function)
    
    elif len(parameters) == 3:
        # Three parameters tool
        param1 = parameters[0]
        param2 = parameters[1]
        param3 = parameters[2]
        param1_name = param1['name']
        param2_name = param2['name']
        param3_name = param3['name']
        param1_desc = param1.get('description', f'The {param1_name} parameter')
        param2_desc = param2.get('description', f'The {param2_name} parameter')
        param3_desc = param3.get('description', f'The {param3_name} parameter')
        param1_required = param1.get('required', False)
        param2_required = param2.get('required', False)
        param3_required = param3.get('required', False)
        param1_default = param1.get('defaultValue', '')
        param2_default = param2.get('defaultValue', '')
        param3_default = param3.get('defaultValue', '')
        
        if param1_required and param2_required and param3_required:
            async def tool_function(context: RunContext, param1_value: str, param2_value: str, param3_value: str) -> str:
                data = {param1_name: param1_value, param2_name: param2_value, param3_name: param3_value}
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
            
            # Set function metadata
            tool_function.__name__ = tool_name
            tool_function.__doc__ = tool_docstring
            return function_tool()(tool_function)
        else:
            # For mixed required/optional parameters, create appropriate signature
            # This is a simplified version - you can expand based on your needs
            async def tool_function(context: RunContext, 
                                   param1_value: str = param1_default if not param1_required else None,
                                   param2_value: str = param2_default if not param2_required else None,
                                   param3_value: str = param3_default if not param3_required else None) -> str:
                data = {param1_name: param1_value, param2_name: param2_value, param3_name: param3_value}
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
            
            # Set function metadata
            tool_function.__name__ = tool_name
            tool_function.__doc__ = tool_docstring
            return function_tool()(tool_function)
    
    else:
        # For 4+ parameters, we'll use a more generic approach
        logging.info(f"Creating tool {tool_name} with {len(parameters)} parameters")
        
        # Build parameter list for function signature
        required_params = [p for p in parameters if p.get('required', False)]
        optional_params = [p for p in parameters if not p.get('required', False)]
        
        # This template is not used directly, just for reference
        
        # For now, we'll create a simpler version that handles up to 5 parameters
        if len(parameters) <= 5:
            # Generate function with exact parameter count
            param_names = [p['name'] for p in parameters]
            param_args = []
            data_dict_items = []
            
            for i, param in enumerate(parameters):
                param_var = f"param{i+1}"
                if param.get('required', False):
                    param_args.append(f"{param_var}: str")
                else:
                    default_val = param.get('defaultValue', '')
                    param_args.append(f"{param_var}: str = '{default_val}'")
                data_dict_items.append(f"'{param['name']}': {param_var}")
            
            params_str = ", ".join(param_args)
            data_dict_str = "{" + ", ".join(data_dict_items) + "}"
            
            # Create the function dynamically
            async def tool_function(*args, **kwargs):
                # Extract context and parameters
                context = args[0]
                param_values = args[1:]
                
                # Build data dictionary
                data = {}
                for i, param in enumerate(parameters):
                    if i < len(param_values):
                        data[param['name']] = param_values[i]
                    else:
                        data[param['name']] = param.get('defaultValue', '')
                
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
            
            # Set function metadata
            tool_function.__name__ = tool_name
            tool_function.__doc__ = tool_docstring
            return function_tool()(tool_function)
        else:
            # Too many parameters - log warning but still try to create
            logging.warning(f"Tool {tool_name} has {len(parameters)} parameters which may cause issues")
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
        elif tool_name == 'send_email':
            dynamic_tools.append(send_email)
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