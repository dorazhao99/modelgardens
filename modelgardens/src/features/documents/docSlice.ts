import { createSlice } from '@reduxjs/toolkit'
import type { PayloadAction } from '@reduxjs/toolkit';


interface Document {
    title: string, 
    url: string,
    content: string
}

interface Documents {
    [key: string]: Document
}

const initialState:Documents = {}

const docSlice = createSlice({
  name: 'documents',
  initialState,
  reducers: {
    addDocument: (state, action) => {
        const newState = {...state}
        newState[action.payload.id] = action.payload.document
        return newState
       
    },
    updateContent: (state, action) => {
        const id = action.payload.id;
        if (id in state) {
            state[id].content = action.payload.content;
        }
    }
  },
})

export const { addDocument, updateContent } = docSlice.actions
export default docSlice.reducer