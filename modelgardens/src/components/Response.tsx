// components/TextInput.tsx

import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"

export function Response() {
  return (
    <div className="flex items-center gap-4`">
        <div>
          <h4>
            [1]
          </h4>
        </div>
        <Textarea placeholder="" />
    </div>
  )
}