import { NodeEditor, ClassicPreset } from "rete";
import type { Schemes } from "./editor";


export async function removeConnections(
  editor: NodeEditor<Schemes>,
  nodeId: any
) {
  for (const c of [...editor.getConnections()]) {
    if (c.source === nodeId || c.target === nodeId) {
      await editor.removeConnection(c.id);
    }
  }
}

export async function clearEditor(editor: NodeEditor<Schemes>) {
  for (const c of [...editor.getConnections()]) {
    await editor.removeConnection(c.id);
  }
  for (const n of [...editor.getNodes()]) {
    await editor.removeNode(n.id);
  }
}

/**
 * Input control options
 */
type InputControlOptions<N> = {
  /** Whether the control is readonly. Default is `false` */
  readonly?: boolean,
  /** Initial value of the control */
  initial?: N,
  /** Callback function that is called when the control value changes */
  change?: (value: N) => void
}
/**
 * The input control class
 * @example new InputControl('text', { readonly: true, initial: 'hello' })
 */
export class CustomInputControl<T extends 'text' | 'number', N = T extends 'text' ? string : number> extends ClassicPreset.InputControl<T, N> {
  // value?: N
  // readonly: boolean

  /**
   * @constructor
   * @param type Type of the control: `text` or `number`
   * @param label Label of the output port ==>## Customize add.
   * @param options Control options
   */
  constructor(public type: T, public label: string='',
      public options?: InputControlOptions<N>, public hide: boolean=false
  ) {
    super(type, options)
    this.label = label; // label of input controle
    this.hide = hide;   // show or hide
  }
}
