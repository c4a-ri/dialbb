import type { BaseSchemes } from 'rete'

import { ContextMenuPlugin } from '.'

export type Position = { x: number, y: number }

/**
 * Item type of context menu
 */
export type Item = {
  label: string
  key: string
  handler(): void
  subitems?: Item[]
}

export type ItemsCollection = {
  searchBar?: boolean,
  list: Item[]
}

export type Items<Schemes extends BaseSchemes> = (
  context: 'root' | Schemes['Node'],
  plugin: ContextMenuPlugin<Schemes>
) => ItemsCollection
