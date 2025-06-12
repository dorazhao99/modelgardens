import { OpenAI } from "openai"


const client= new OpenAI({
  apiKey: "KEY", 
  dangerouslyAllowBrowser: true  // Make sure this is set in your env
})

interface Message {
    role: string, 
    content: string
}

export async function askOpenAI(messages: Array<Message>): Promise<string> {
  const chatCompletion = await client.chat.completions.create({
    model: "gpt-4o-mini", // or "gpt-4" if you have access
    messages: messages,
  })

  return chatCompletion.choices[0].message.content?.trim() || ""
}

export function getCutoff(cells: Array<unknown>, cellNumber: number) {
    let cutoff = 0 
    let cellIdx = 0
    console.log(cellNumber)
    for (let i = 0; i < cellNumber; i++) {
        cutoff += 1
        if (cells[i].output.length > 0) {
            cutoff += 1
        }
    }
    cutoff += 1
    return cutoff
}