import { useState, useEffect } from 'react'
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { Play, PlusCircle, Trash2, ArrowDownFromLine, Loader2Icon } from "lucide-react"

export function Cell(props:any) {
  const params = props.cellParams
  const idx = props.idx
  const [text, setText] = useState(params.text)
  const [isLoading, setLoading] = useState(props.isLoading)

  useEffect(() => {
    setText(params.text)
  }, [params.text])


  useEffect(() => {
    if (params.runs === "*") {
      setLoading(true)
    } else {
      setLoading(false)
    }

  }, [params.runs])

  function onRun(idx: number, text: string, runFunction: (idx: number, text: string) => void) {
    setLoading(true)
    runFunction(idx, text)
  }

  return (
    <div>
      <div className="flex items-center gap-4`">
          <div>
            <h5>
              {params.runs > 0 ? `[${params.runs}]` : "[]"}
            </h5>
          </div>
          <Textarea value={text} placeholder={params.text} onChange={(e) => setText(e.target.value)} />
          <div className="flex flex-col gap-1">
            <Button variant="secondary" size="icon" className="size-4" onClick={() => onRun(idx, text, props.onClick)}>
              <Play />
            </Button>
            <Button variant="secondary" size="icon" className="size-4" onClick={() => props.addCell(idx)}>
              <PlusCircle/>
            </Button>
            <Button variant="secondary" size="icon" className="size-4" onClick={() => props.deleteCell(idx)}>
              <Trash2/>
            </Button>
              <Button variant="secondary" size="icon" className="size-4" onClick={() => onRun(idx, text, props.runThisAndBelow)}>
              <ArrowDownFromLine />
            </Button>
          </div>
      </div>
      <div>
        {
          isLoading ? (
            <Button size="sm" disabled>
              <Loader2Icon className="animate-spin" />
              Generating response
            </Button>

          ) : (params.output)
        }
      </div>
    </div>
  )
}