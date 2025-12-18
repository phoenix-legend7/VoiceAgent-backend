from openai import OpenAI
from app.core.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)


async def generate_prompt_with_openai(
    agent_name: str,
    industry: str,
    description: str = None,
    purpose: str = None,
    personality: str = None,
    industry_prompt: str = None,
) -> str:
    """
    Generate an optimized agent prompt using OpenAI.
    
    Args:
        agent_name: Name of the agent
        industry: Industry type
        description: Optional compiled description from wizard
        purpose: Optional primary purpose
        personality: Optional personality traits
        industry_prompt: Base industry-specific prompt
    
    Returns:
        Generated prompt string
    """

    # Build context from provided fields
    context_parts = []
    
    if description:
        context_parts.append(f"Additional context: {description}")
    else:
        if purpose:
            context_parts.append(f"Primary purpose: {purpose}")
        if personality:
            context_parts.append(f"Personality: {personality}")
    
    context = "\n".join(context_parts) if context_parts else "No additional context provided"
    
    system_prompt = """You are an expert AI prompt engineer. Your task is to create a comprehensive, 
professional system prompt for an AI agent. The prompt should be clear, detailed, and optimized for 
the agent to perform its role effectively."""
    
    user_message = f"""Generate a professional system prompt for an AI agent with the following specifications:

Agent Name: {agent_name}
Industry: {industry}
Industry Guidelines: {industry_prompt if industry_prompt else "General customer service"}
Additional Context: 
{context}

Create a comprehensive prompt that:
1. Clearly defines the agent's role and purpose
2. Sets expectations for professional behavior
3. Includes specific guidance based on the industry
4. Incorporates the personality and context provided
5. Is suitable for a voice-based conversational AI
6. Ends with clear operational boundaries

Provide only the prompt content, no preamble."""
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        temperature=0.7,
        max_tokens=1000,
    )
    
    return response.choices[0].message.content.strip()
