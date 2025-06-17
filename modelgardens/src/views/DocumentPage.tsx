import { useState, useEffect, useRef } from "react"
import { SidebarProvider, SidebarTrigger, SidebarInset } from "@/components/ui/sidebar"
import { AppSidebar } from "@/components/AppSidebar"
import TextEditor from "@/components/Editor"
import { NewLayerDialog } from "@/components/NewLayerDialog"
import { EditLayersDialog } from "@/components/EditLayersDialog"
import { Button } from "@/components/ui/button"
import { prompts, knowledgeManager } from "@/prompts"
import { askOpenAI } from "@/utils"
import { Loader2Icon, Save, Pen } from "lucide-react"
import { useParams } from "react-router-dom"
import { useDispatch, useSelector } from "react-redux"
import { updateContent } from "@/features/documents/docSlice"
import { addEdits } from "@/features/knowledge/knowledgeSlice"

interface Layer {
  name: string, 
  prompt: string,
}

interface BooleanDict {
  [key: number]: boolean
}


const DocumentPage = () => {
  const { id } = useParams()
  const editorRef = useRef()

  const dispatch = useDispatch()
  const storeDocuments = useSelector((state: RootState) => state.documents)
  const know = useSelector((state: RootState) => state.knowledge.baseKnowledge)
  const [selectedLayers, setSelection] = useState<BooleanDict>({})
  const initialDocument =  storeDocuments[id] ? storeDocuments[id].content : ""
  const [content, setContent] = useState<string>(initialDocument)
  const [isLoading, setLoading] = useState<boolean>(false)
  const [isSaving, setSaving] = useState<boolean>(false)

  useEffect(() => {
    let pageDocument = storeDocuments[id] ? storeDocuments[id].content : ""
    setContent(pageDocument)
  }, [id])

  const layers: Array<Layer> = [
    {
      name: "Dating App", prompt: prompts.dating_app, 
    }, 
    {
      name: "Speaker Bio", prompt: prompts.speaker_bio, 
    },
    {
      name: "Tweet Thread", prompt: prompts.tweet_thread
    }
  ]

  const addLayer = (idx: number) => {
    const newLayers = {
        ...selectedLayers
    }

    if (idx in newLayers && newLayers[idx] === true) {
      newLayers[idx] = false 
    } else {
      newLayers[idx] = true 
    }
    setSelection(newLayers)
  }

  const generateContent = async () => {
    setLoading(true)
    const promptLayers:Array<string> = []
    Object.keys(selectedLayers).forEach((layerIdx, _) => {
      // console.log(layerIdx, selectedLayers[layerIdx])
      if (selectedLayers[layerIdx] === true) {
        promptLayers.push(layers[layerIdx].prompt)
      }
    })
    const systemPrompt = promptLayers.join('\n')
    const input =  [{'role': 'system', 'content': systemPrompt}, {'role': 'user', 'content': know}]
    console.log(input, selectedLayers, promptLayers)
    const response = await askOpenAI(input)
    setContent(response)
    setLoading(false)
  }

  const updateDocument = () => {
    editorRef.current?.relayData(); 
  }

  const handleSave = async(data: string) => {
    setSaving(true)
    dispatch(updateContent({id: id, content: data}))
    const input =  [{'role': 'system', 'content': knowledgeManager}, {'role': 'user', 'content': `## Knowledge Base ${know}\n ## Document ${data}`}]
    const response = await askOpenAI(input)
    dispatch(addEdits(response))
    setSaving(false)
  }

  return (
    <div>
      <SidebarProvider>
        <AppSidebar/>
        <SidebarInset className="-ml-1">
          <header className="flex h-16 shrink-0">
            <SidebarTrigger/>
          </header>
          <div className="flex flex-1 flex-col gap-4 items-start">
            <div className="flex flex-row gap-4 items-center">
              <h2>Document {id}</h2>
              <NewLayerDialog 
                layers={layers}
                selectedLayers={selectedLayers}
                addLayer={addLayer}
                generateContent={generateContent}
              />
              <EditLayersDialog/>
              
              {/* <Button className="cursor-pointer rounded-xl" size="sm" variant="secondary">
                <Pen />
                Create New Layer
              </Button> */}
              </div>
            <div className="flex flex-col w-full">
              <div>
                {isLoading ? (
                  <Button size="sm" disabled>
                    <Loader2Icon className="animate-spin" />
                    Generating document
                  </Button>
                ) : null}
              </div>
              <div className="w-full">
                <TextEditor ref={editorRef} onDataRelay={handleSave} content={content}/>
              </div>
            </div>
            <div className="flex flex-row gap-2">
              <Button className="cursor-pointer" size="sm" onClick={updateDocument}>
                {
                  isSaving ? (
                    <span className="flex flex-row gap-2 items-center">
                      <Loader2Icon className="animate-spin" />
                      Saving...
                    </span>
                  ) : (
                    <span className="flex flex-row gap-2 items-center">
                      <Save/>
                      Save Document
                    </span>
                  )
                }
              </Button>
            </div>
          </div>
        </SidebarInset>
        {/* <main className="bg-blue-200 width-full">
          <SidebarTrigger />
        </main> */}
      </SidebarProvider>

    </div>
  )
}

export default DocumentPage