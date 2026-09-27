import type { Chapter, Evaluation, EnhancedPrompt } from './types'

export const chapters: Chapter[] = [
  {
    id: '1',
    title: 'Introduction to Prompt Engineering',
    description: 'Learn the fundamentals of crafting effective prompts for AI systems',
    duration: '15 min',
    lessons: 4,
    progress: 0,
    content: `# Introduction to Prompt Engineering

Prompt engineering is the art and science of crafting effective instructions for AI systems. In this chapter, you'll learn the foundational concepts that will help you communicate more effectively with AI models.

## What is a Prompt?

A prompt is any text input you provide to an AI model to generate a response. The quality of your prompt directly influences the quality of the output you receive.

## Why Does Prompt Engineering Matter?

- **Precision**: Well-crafted prompts lead to more accurate and relevant responses
- **Efficiency**: Good prompts reduce the need for follow-up questions
- **Consistency**: Structured prompts produce more reliable outputs
- **Control**: You can guide the AI's behavior, tone, and format

## Key Principles

1. **Be Specific**: Vague prompts lead to vague answers
2. **Provide Context**: Help the AI understand your situation
3. **Set Expectations**: Define the format and scope of the response
4. **Iterate**: Refine your prompts based on the outputs you receive`,
    videoUrl: 'https://example.com/intro-video'
  },
  {
    id: '2',
    title: 'Clarity and Specificity',
    description: 'Master the art of writing clear and specific prompts',
    duration: '20 min',
    lessons: 5,
    progress: 0,
    content: `# Clarity and Specificity

The most common mistake in prompt engineering is being too vague. This chapter focuses on techniques to make your prompts crystal clear.

## The Problem with Vague Prompts

Consider this prompt: "Tell me about marketing."

This could mean:
- History of marketing
- Digital marketing strategies
- Marketing career advice
- Marketing budget allocation

## Techniques for Clarity

### 1. Define Your Audience
"Explain marketing strategies **for a small business owner** with no prior experience."

### 2. Specify the Format
"Provide a **bulleted list** of 5 marketing tips."

### 3. Set Boundaries
"Focus only on **social media marketing** for B2B companies."

### 4. Include Examples
"Write a marketing email **similar to** this example: [example]"

## Practice Exercise

Transform this vague prompt into a specific one:
- Vague: "Help me with my resume"
- Specific: "Review my software engineering resume for a senior position at a tech startup. Focus on quantifying achievements and highlighting leadership experience."`,
  },
  {
    id: '3',
    title: 'Context and Background',
    description: 'Learn how to provide effective context in your prompts',
    duration: '18 min',
    lessons: 4,
    progress: 0,
    content: `# Context and Background

Context is the information that helps an AI understand your specific situation, needs, and constraints.

## Why Context Matters

AI models don't know:
- Your specific situation
- Your prior knowledge level
- Your industry or domain
- Your goals and constraints

## Types of Context

### 1. Situational Context
"I'm a **first-year medical student** preparing for my anatomy exam."

### 2. Goal Context
"I need to **convince my manager** to approve a new software tool."

### 3. Constraint Context
"The solution must work **within a $500 budget** and **be implemented in 2 weeks**."

### 4. Historical Context
"Previously, we tried X approach but it failed because Y."

## Context Framework

Use this framework for comprehensive context:
1. **Who**: Who are you? Who is the audience?
2. **What**: What exactly do you need?
3. **Why**: Why do you need it?
4. **When**: Any time constraints?
5. **Where**: Any location or platform constraints?
6. **How**: Any specific methods or approaches required?`,
  },
  {
    id: '4',
    title: 'Role-Based Prompting',
    description: 'Assign roles to AI for more specialized responses',
    duration: '22 min',
    lessons: 6,
    progress: 0,
    content: `# Role-Based Prompting

Assigning a role to the AI can dramatically improve the quality and relevance of responses.

## What is Role-Based Prompting?

Instead of asking a generic question, you instruct the AI to respond as if it were a specific expert or persona.

## Examples

### Expert Role
"You are a **senior financial advisor** with 20 years of experience. A client asks you about retirement planning strategies."

### Perspective Role
"You are a **skeptical investor** evaluating this startup pitch. What concerns would you raise?"

### Character Role
"You are a **patient teacher** explaining calculus to a struggling high school student."

## Benefits of Role-Based Prompting

1. **Expertise**: Access specialized knowledge and terminology
2. **Perspective**: Get diverse viewpoints on a topic
3. **Tone**: Match the communication style to your needs
4. **Consistency**: Maintain a coherent voice throughout

## Advanced Technique: Multi-Role

"First, respond as a **marketing expert**, then as a **financial analyst**, then synthesize both perspectives."`,
  },
  {
    id: '5',
    title: 'Chain of Thought Prompting',
    description: 'Guide AI through complex reasoning step by step',
    duration: '25 min',
    lessons: 5,
    progress: 0,
    content: `# Chain of Thought Prompting

For complex problems, guiding the AI through a step-by-step reasoning process significantly improves accuracy.

## What is Chain of Thought?

Chain of Thought (CoT) prompting encourages the AI to show its reasoning process rather than jumping directly to an answer.

## Simple CoT Trigger

Add this phrase to your prompts:
"**Let's think through this step by step.**"

## Explicit CoT Structure

"Solve this problem by:
1. First, identify the key variables
2. Then, list the relevant constraints
3. Next, consider possible approaches
4. Finally, evaluate and select the best solution"

## When to Use CoT

- Math and logic problems
- Multi-step planning
- Analysis and evaluation
- Debugging code
- Complex decision-making

## Example

Without CoT: "What's 17 * 24?"
With CoT: "Calculate 17 * 24. Show your work step by step, breaking it into simpler calculations."

The CoT approach often catches errors that would occur with direct answers.`,
  },
  {
    id: '6',
    title: 'Advanced Techniques',
    description: 'Explore few-shot learning, temperature control, and more',
    duration: '30 min',
    lessons: 7,
    progress: 0,
    content: `# Advanced Prompt Engineering Techniques

This chapter covers sophisticated techniques used by prompt engineering professionals.

## Few-Shot Learning

Provide examples of the input-output pattern you want:

"Convert these sentences to formal English:

Casual: gonna grab some coffee
Formal: I am going to get some coffee

Casual: wanna hang out later?
Formal: Would you like to spend time together later?

Casual: that meeting was a total waste
Formal: [AI completes this]"

## Negative Prompting

Specify what you DON'T want:
"Explain quantum computing. **Do not** use technical jargon. **Do not** assume prior physics knowledge."

## Output Formatting

"Respond in the following JSON format:
{
  "summary": "...",
  "key_points": ["...", "..."],
  "confidence": 0-100
}"

## Iterative Refinement

1. Start with a basic prompt
2. Analyze the response
3. Identify gaps or issues
4. Refine and add constraints
5. Repeat until satisfied

## Meta-Prompting

"Before answering, identify any ambiguities in my question and ask clarifying questions."

This technique helps ensure the AI fully understands your needs before responding.`,
  }
]

export const practiceProblems = [
  {
    id: '1',
    statement: "You need to write a prompt that asks an AI to help you create a marketing email for a new product launch. The product is a smart water bottle that tracks hydration levels.",
    hints: [
      "Consider specifying the target audience",
      "Define the tone and style of the email",
      "Include any constraints like word count or format"
    ]
  },
  {
    id: '2',
    statement: "Create a prompt that instructs an AI to review and improve a piece of code. The code is a Python function that calculates the average of a list of numbers.",
    hints: [
      "Specify what aspects to review (efficiency, readability, edge cases)",
      "Ask for explanations of suggested changes",
      "Consider requesting alternative implementations"
    ]
  },
  {
    id: '3',
    statement: "Write a prompt that asks an AI to help you prepare for a job interview. The position is for a Senior Software Engineer at a fintech company.",
    hints: [
      "Specify the type of questions you want to practice",
      "Include context about your background",
      "Define the format of the mock interview"
    ]
  },
  {
    id: '4',
    statement: "Create a prompt that instructs an AI to analyze a dataset and provide insights. The dataset contains monthly sales data for an e-commerce store over the past 2 years.",
    hints: [
      "Specify what types of insights you're looking for",
      "Define the format for presenting the analysis",
      "Include any specific metrics or KPIs to focus on"
    ]
  },
  {
    id: '5',
    statement: "Write a prompt that asks an AI to help you write a technical blog post about microservices architecture for a developer audience.",
    hints: [
      "Specify the target expertise level of readers",
      "Define the structure and length of the post",
      "Include any specific topics or examples to cover"
    ]
  }
]

export function generateFeedback(prompt: string): Evaluation {
  const wordCount = prompt.split(/\s+/).length
  const hasContext = prompt.toLowerCase().includes('context') || 
                     prompt.toLowerCase().includes('background') ||
                     prompt.length > 100
  const hasSpecificity = prompt.includes('specific') || 
                         prompt.includes('exactly') ||
                         /\d+/.test(prompt)
  const hasRole = prompt.toLowerCase().includes('you are') ||
                  prompt.toLowerCase().includes('act as') ||
                  prompt.toLowerCase().includes('expert')
  const hasFormat = prompt.toLowerCase().includes('format') ||
                    prompt.toLowerCase().includes('list') ||
                    prompt.toLowerCase().includes('bullet')
  
  let score = 40
  let clarity = 50
  let structure = 50
  let specificity = 50
  
  if (wordCount > 20) { score += 10; clarity += 10 }
  if (wordCount > 50) { score += 10; clarity += 10 }
  if (hasContext) { score += 15; structure += 20 }
  if (hasSpecificity) { score += 10; specificity += 25 }
  if (hasRole) { score += 10; structure += 15 }
  if (hasFormat) { score += 5; structure += 10 }
  
  score = Math.min(score, 95)
  clarity = Math.min(clarity, 95)
  structure = Math.min(structure, 95)
  specificity = Math.min(specificity, 95)
  
  const strengths: string[] = []
  const weaknesses: string[] = []
  const suggestions: string[] = []
  
  if (hasContext) {
    strengths.push("Good use of contextual information")
  } else {
    weaknesses.push("Lacks sufficient context")
    suggestions.push("Add background information about your situation or goals")
  }
  
  if (hasSpecificity) {
    strengths.push("Contains specific details and constraints")
  } else {
    weaknesses.push("Could be more specific")
    suggestions.push("Include specific numbers, examples, or constraints")
  }
  
  if (hasRole) {
    strengths.push("Effective use of role-based prompting")
  } else {
    suggestions.push("Consider assigning a role or expertise to the AI")
  }
  
  if (hasFormat) {
    strengths.push("Clear output format specification")
  } else {
    weaknesses.push("No specified output format")
    suggestions.push("Specify how you want the response formatted")
  }
  
  if (wordCount < 20) {
    weaknesses.push("Prompt is too brief")
    suggestions.push("Expand your prompt with more details")
  } else if (wordCount > 30) {
    strengths.push("Good level of detail")
  }
  
  return {
    score,
    clarity,
    structure,
    specificity,
    strengths,
    weaknesses,
    suggestions
  }
}

export function enhancePrompt(original: string): EnhancedPrompt {
  const improvements: string[] = []
  let enhanced = original
  
  if (!original.toLowerCase().includes('you are') && !original.toLowerCase().includes('act as')) {
    enhanced = `You are an expert assistant. ${enhanced}`
    improvements.push("Added a role assignment for more focused responses")
  }
  
  if (!original.toLowerCase().includes('format') && !original.toLowerCase().includes('provide') && !original.toLowerCase().includes('list')) {
    enhanced = `${enhanced} Please provide your response in a clear, structured format with bullet points for key information.`
    improvements.push("Added output format specification for clarity")
  }
  
  if (original.split(/\s+/).length < 30) {
    enhanced = `${enhanced} Be thorough in your explanation and include relevant examples where appropriate.`
    improvements.push("Added instructions for comprehensive coverage")
  }
  
  if (!original.toLowerCase().includes('step') && !original.toLowerCase().includes('first')) {
    enhanced = `${enhanced} Walk through your reasoning step by step.`
    improvements.push("Added chain-of-thought instruction for better reasoning")
  }
  
  if (improvements.length === 0) {
    improvements.push("Your prompt is already well-structured!")
    improvements.push("Consider adding specific examples for even better results")
  }
  
  return {
    original,
    enhanced,
    improvements
  }
}
