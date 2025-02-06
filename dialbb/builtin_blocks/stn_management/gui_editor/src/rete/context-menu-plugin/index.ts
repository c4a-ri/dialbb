import { Scope } from 'rete'
import type { BaseSchemes } from 'rete'
import { BaseAreaPlugin } from 'rete-area-plugin'
import type { BaseArea, RenderSignal } from 'rete-area-plugin'

import type { Item, Items, Position } from './types'

export * as Presets from './presets'

/**
 * Context menu plugin props
 * @priority 8
 */
export type Props<Schemes extends BaseSchemes> = {
  /** delay before hiding context menu */
  delay?: number
  /** menu items, can be produced by preset */
  items: Items<Schemes>
}
export type RenderMeta = { filled?: boolean }

/**
 * Signal types produced by ContextMenuPlugin instance
 * @priority 10
 */
export type ContextMenuExtra =
  | RenderSignal<'contextmenu', {
    items: Item[]
    onHide(): void
    searchBar?: boolean
  }>

type Requires<Schemes extends BaseSchemes> =
  | { type: 'contextmenu', data: { event: MouseEvent, context: 'root' | Schemes['Node'] | Schemes['Connection'] } }
  | { type: 'unmount', data: { element: HTMLElement } }
  | { type: 'pointerdown', data: { position: Position, event: PointerEvent } }

/**
 * Plugin for context menu.
 * Responsible for initialing rendering of context menu with predefined items.
 * @priority 9
 * @emits render
 * @emits unmount
 * @listens unmount
 * @listens contextmenu
 * @listens pointerdown
 */
export class ContextMenuPlugin<Schemes extends BaseSchemes> extends Scope<never, [Requires<Schemes> | ContextMenuExtra]> {
  /**
   * @param props Properties
   */
  constructor(private props: Props<Schemes>) {
    super('context-menu')
  }

  setParent(scope: Scope<Requires<Schemes>>): void {
    super.setParent(scope)

    const area = this.parentScope<BaseAreaPlugin<Schemes, BaseArea<Schemes>>>(BaseAreaPlugin)
    const container: HTMLElement = (area as any).container

    if (!container || !(container instanceof HTMLElement)) throw new Error('container expected')

    const element = document.createElement('div')

    element.style.display = 'none'
    element.style.position = 'fixed'

    // eslint-disable-next-line max-statements
    this.addPipe(context => {
      const parent = this.parentScope()

      if (!context || typeof context !== 'object' || !('type' in context)) return context
      if (context.type === 'unmount') {
        if (context.data.element === element) {
          element.style.display = 'none'
        }
      } else if (context.type === 'contextmenu') {
        context.data.event.preventDefault()
        context.data.event.stopPropagation()

        const { searchBar, list } = this.props.items(context.data.context, this)

        container.appendChild(element)
        element.style.left = `${context.data.event.clientX}px`
        element.style.top = `${context.data.event.clientY}px`
        element.style.display = ''

        parent.emit({
          type: 'render',
          data: {
            type: 'contextmenu',
            element,
            searchBar,
            onHide() {
              parent.emit({ type: 'unmount', data: { element } })
            },
            items: list
          }
        })
      } else if (context.type === 'pointerdown') {
        if (!context.data.event.composedPath().includes(element)) {
          parent.emit({ type: 'unmount', data: { element } })
        }
      }
      return context
    })
  }
}
