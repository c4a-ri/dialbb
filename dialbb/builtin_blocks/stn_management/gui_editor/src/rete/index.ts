import { createEditor as createInsertEditor } from './editor'

const createEditor = createInsertEditor

if (!createEditor) {
  throw new Error(`template with name ${name} not found`)
}

export {
  createEditor
}
