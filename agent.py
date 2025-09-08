from dotenv import load_dotenv
import logging

from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import (
    noise_cancellation,
)
from livekit.plugins import google
from config_loader import config_loader
from tools import get_dynamic_tools, search_web
load_dotenv()


class Assistant(Agent):
    def __init__(self) -> None:
        # Load configuration from Firebase
        config = config_loader.load_configuration()
        
        # Get dynamic tools based on configuration
        dynamic_tools = get_dynamic_tools(config.get('tools', []))
        
        # Log all available tools
        logging.info("🛠️  === AGENT TOOLS AVAILABLE ===")
        for i, tool in enumerate(dynamic_tools, 1):
            tool_name = getattr(tool, '__name__', 'unknown')
            tool_doc = getattr(tool, '__doc__', 'No description')
            logging.info(f"🔧 Tool {i}: {tool_name} - {tool_doc}")
        logging.info(f"📊 Total tools available: {len(dynamic_tools)}")
        logging.info("🛠️  ===========================")
        
        # Create tool reference for prompt
        tool_list = []
        for tool in dynamic_tools:
            tool_name = getattr(tool, '__name__', 'unknown')
            tool_doc = getattr(tool, '__doc__', 'No description')
            tool_list.append(f"- {tool_name}: {tool_doc}")
        
        tools_reference = "\n".join(tool_list)
        base_instructions = config.get('agentInstruction', 'You are a helpful AI assistant.')
        
        # Create dynamic tool usage guidelines based on available tools
        tool_names = [getattr(tool, '__name__', 'unknown') for tool in dynamic_tools]
        
        guidelines = []
        if 'search_web' in tool_names:
            guidelines.append("- When users ask questions that require external information, USE the search_web tool")
        if 'end_call' in tool_names:
            guidelines.append("- When users say goodbye, want to hang up, or the conversation is complete, USE the end_call tool")
        
        guidelines.append("- When users ask for specific data or APIs, USE the appropriate custom tools")
        guidelines.append("- Always try to use relevant tools rather than saying you cannot help")
        guidelines.append("- Be proactive in using tools to provide accurate and helpful responses")
        guidelines.append("- If you don't have a tool for a specific task, clearly tell the user you cannot perform that action")
        
        guidelines_text = "\n".join(guidelines)
        
        # Add tools reference to instructions with dynamic guidance
        enhanced_instructions = f"""{base_instructions}

IMPORTANT - YOU HAVE ACCESS TO THESE TOOLS:
{tools_reference}

TOOL USAGE GUIDELINES:
{guidelines_text}

Use these tools actively and appropriately to assist users effectively."""
        
        super().__init__(
            instructions=enhanced_instructions,
            llm=google.beta.realtime.RealtimeModel(
            voice="Aoede",
            temperature=0.1,
            vertexai=False
        ),
            tools=dynamic_tools,

        )
        


async def entrypoint(ctx: agents.JobContext):
    # Load configuration from Firebase
    config = config_loader.load_configuration()
    begin_message = config.get('beginMessage', "Hello! I'm your AI assistant. How can I help you today?")
    session_instruction = config_loader.get_session_instruction(begin_message)
    
    session = AgentSession()

    try:
        await session.start(
            room=ctx.room,
            agent=Assistant(),
            room_input_options=RoomInputOptions(
                # LiveKit Cloud enhanced noise cancellation
                # - If self-hosting, omit this parameter
                # - For telephony applications, use `BVCTelephony` for best results
                video_enabled=True,
                noise_cancellation=noise_cancellation.BVC(),
            ),
        )

        await ctx.connect()

        # Start the session reply generation (this handles the conversation)
        await session.generate_reply(instructions=session_instruction)
        
    except Exception as e:
        logging.error(f"❌ Error in entrypoint: {e}")
        raise


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint, agent_name="calldash-agent-beta"))