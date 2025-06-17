import { BIO_EXAMPLE } from '@/template';
import { createSlice } from '@reduxjs/toolkit'
import type { PayloadAction } from '@reduxjs/toolkit';

interface Edits {
    update: string, 
    original_fact: string,
    updated_fact: string
}

interface Knowledge {
    baseKnowledge: string, 
    edits: Edits[]
}

  const testAlert = [
    {
      'update': 'edit', 
      'original_fact': 'Test1',
      'updated_fact': 'New Test1'
    },
        {
      'update': 'add', 
      'original_fact': 'Test2',
      'updated_fact': 'New Test1'
    }
  ]
const initialState:Knowledge = {
  baseKnowledge: BIO_EXAMPLE,
  edits: []
}

const knowledgeSlice = createSlice({
  name: 'knowledge',
  initialState,
  reducers: {
    addEdits: (state, action) => {
      console.log(action.payload)
      const rawResponse = action.payload
      const jsonText = rawResponse
      .trim()
      .replace(/^```json\s*/, '')  // Remove opening ```json
      .replace(/^```/, '')         // Edge case: standalone ``` if no language specified
      .replace(/```$/, '');        // Remove trailing ```
      const newEdits = JSON.parse(jsonText)['changes']
      return {
        ...state, 
        edits: [...state.edits, ...newEdits]
      }
    },
    acceptEdits: (state, action) => {
      const idx = action.payload
      const edit = state.edits[idx]
      if (edit.update === 'add') {
        state.baseKnowledge = state.baseKnowledge + '\n' + edit.updated_fact
      }
      const newEdits = state.edits.filter((_, index) => index !== idx);
      state.edits = newEdits
    }, 
    rejectEdits: (state, action) => {
      const idx = action.payload
      const newEdits = state.edits.filter((_, index) => index !== idx);
      state.edits = newEdits
    },
    updateKB: (state, action) => {
      state.baseKnowledge = action.payload
    }
  },
})

export const { addEdits, acceptEdits, rejectEdits, updateKB } = knowledgeSlice.actions
export default knowledgeSlice.reducer