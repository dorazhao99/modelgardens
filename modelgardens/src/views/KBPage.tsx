import { useState, useRef } from "react"
import { useSelector, useDispatch } from "react-redux"
import { SidebarProvider, SidebarTrigger, SidebarInset } from "@/components/ui/sidebar"
import { AppSidebar } from "@/components/AppSidebar"
import TextEditor from "@/components/Editor"
import { ChangeAlert } from "@/components/ChangeAlert"
import { Loader2Icon, Save } from "lucide-react"
import { Button } from "@/components/ui/button"
import { updateKB } from "@/features/knowledge/knowledgeSlice"

const KnowledgePage = () => {
  const dispatch = useDispatch()
  const [isSaving, setSaving] = useState(false)
  const knowledgeBase = useSelector((state: RootState) => state.knowledge.baseKnowledge)
  const edits = useSelector((state: RootState) => state.knowledge.edits)
  const editorRef = useRef() 

   const saveKB = () => {
    editorRef.current?.relayData(); 
  }

  const handleSave = async(data: string) => {
    setSaving(true)
    dispatch(updateKB(data))
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
              <h2>Knowledge Base</h2>
            </div>
            {
              (edits.length > 0) ? (
                <div className="w-full">
                  <ChangeAlert alertInfo={edits}/>
                </div>
              ) : null
            }
            <div className="flex flex-col w-full">
              <div className="w-full">
                <TextEditor ref={editorRef} onDataRelay={handleSave} content={knowledgeBase}/>
              </div>
            </div>
            <div className="flex flex-row gap-2">
              <Button className="cursor-pointer" size="sm" onClick={saveKB}>
                {
                  isSaving ? (
                    <span className="flex flex-row gap-2 items-center">
                      <Loader2Icon className="animate-spin" />
                      Saving...
                    </span>
                  ) : (
                    <span className="flex flex-row gap-2 items-center">
                      <Save/>
                      Save
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

export default KnowledgePage