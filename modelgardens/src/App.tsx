import { useState } from 'react'
import { Button } from './components/ui/button'
import { Cell } from './components/Cell'
import { Response } from './components/Response'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'
import { askOpenAI, getCutoff } from './utils'

interface ConversationParameter {
    "text": string, 
    "mods": Array<string>,
    "type": string,
    "runs": number | string,
    "output": string
}

interface Message {
    role: string, 
    content: string
}

function App() {
  const blankCell = {"text": "", "mods": [], "type": "cell", "runs": 0, "output": ""}
  const [count, setCount] = useState(0)
  const [transcript, setTranscript] = useState<Array<Message>>([])
  const [conversation, setConversation] = useState([blankCell])

const runCell = async(cellNumber: number, input: string) => {
    console.log("here", transcript)
    // Query OpenAI API 
    const newTranscript:Array<Message> = [...transcript]
    const cutoff:number = getCutoff(conversation, cellNumber)
    console.log('Cutoff', cutoff)
    
    if (cutoff >= newTranscript.length) {
      newTranscript.push({'role': 'user', 'content': input})
    } else {
      newTranscript[cutoff - 1] = {'role': 'user', 'content': input}
    }
    
    console.log(newTranscript)
    const slicedTranscript = [...newTranscript].slice(0, cutoff)
    console.log(slicedTranscript)
    const response = await askOpenAI(slicedTranscript)

    if (cutoff in newTranscript) {
      newTranscript[cutoff] = {'role': 'assistant', 'content': response}
    } else {
      newTranscript.push({'role': 'assistant', 'content': response})
    } 
    setTranscript(newTranscript)
    const responseCell = conversation[cellNumber]
    responseCell.text = input
    responseCell.output = response
    responseCell.runs = count + 1
    setCount(count + 1)
    const newConversation:Array<ConversationParameter> = [...conversation]
    newConversation[cellNumber] = responseCell
    if (cellNumber === conversation.length - 1) {
      newConversation[cellNumber + 1] = blankCell
    }
    setConversation(newConversation)
  }

const helperRun = async(cutoff: number, newTranscript: Array) => {
  const slicedTranscript = [...newTranscript].slice(0, cutoff)
  const response = await askOpenAI(slicedTranscript)
  if (cutoff in newTranscript) {
    newTranscript[cutoff] = {'role': 'assistant', 'content': response}
  } else {
    newTranscript.push({'role': 'assistant', 'content': response})
  } 
  return {response: response, transcript: newTranscript}
}

const processResponse = (responseCell, cellNumber, newConversation) => {
  newConversation[cellNumber] = responseCell
  setConversation(newConversation)
  return newConversation
}

const runThisAndBelow = async(cellNumber: number, input: string) => {
  const convoLength: number = conversation.length
  let newConversation:Array<ConversationParameter> = [...conversation]
  let newTranscript:Array<Message> = [...transcript]
  let cutoff:number = getCutoff(conversation, cellNumber)
  let tempCount = count 

  // set all runs to * meaning loading 
  for (let i = cellNumber; i < convoLength; i++) {
    if (newConversation[i].text.length > 0) {
      newConversation[i].runs = "*"
    }
  }
  setConversation(newConversation)

  if (cutoff >= newTranscript.length) {
    newTranscript.push({'role': 'user', 'content': input})
  } else {
    newTranscript[cutoff - 1] = {'role': 'user', 'content': input}
  }
  
  let helperResponse = await helperRun(cutoff, newTranscript)
   
  newTranscript = helperResponse.transcript
  tempCount += 1
  let currentCell = conversation[cellNumber]
  currentCell.text = input
  currentCell.output = helperResponse.response
  currentCell.runs = tempCount

  newConversation = processResponse(currentCell, cellNumber, newConversation)

  
  for (let i = cellNumber + 1; i < convoLength; i++) {
    if (conversation[i].text.length > 0) {
      console.log('Running', i)
      cutoff = getCutoff(conversation, i)
      helperResponse = await helperRun(cutoff, newTranscript)
      newTranscript = helperResponse.transcript
      tempCount += 1

    
      currentCell = conversation[i]
      currentCell.output = helperResponse.response
      currentCell.runs = tempCount
      newConversation = processResponse(currentCell, i, newConversation)
      setConversation(newConversation)
    }
  }
  setTranscript(newTranscript)
  setCount(tempCount)
}

const addCell = (cellNumber: number) => {
  let newConversation = [...conversation]
  newConversation.splice(cellNumber + 1, 0, blankCell)
  console.log(cellNumber, newConversation)
  
  const cutoff:number = getCutoff(conversation, cellNumber)
  const blankEntry = {"role": "user", "content": ""}
  const newTranscript = [...transcript.slice(0, cutoff + 1), blankEntry, ...transcript.slice(cutoff + 1,)]
  setConversation(newConversation)
  setTranscript(newTranscript)
}

const deleteCell = (cellNumber: number) => {
  const deleted = conversation[cellNumber]

  const newConversation = [...conversation.slice(0, cellNumber), ...conversation.slice(cellNumber + 1,)];
  setConversation(newConversation)
}

  return (
    <>
      <div className="flex flex-col gap-3">
        <ul>
        {
          conversation.map((params, idx) => {
            return(
              <li draggable>
              <Cell
                idx={idx}
                cellParams={params}
                onClick={runCell}
                addCell={addCell}
                deleteCell={deleteCell}
                runThisAndBelow={runThisAndBelow}
              />
              </li>
            )
          })
        }
        </ul>
      </div>
    </>
  )
}

export default App
