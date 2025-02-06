import { ClassicPreset as Classic } from "rete";
import type { DataflowNode } from "rete-engine";
import { socket } from "../sockets";

export class OutputNode
  extends Classic.Node<
    { value: Classic.Socket },
    {},
    { key: Classic.InputControl<"text"> }
  >
  implements DataflowNode {
  width = 180;
  height = 140;

  constructor(initial: string) {
    super("Output");

    this.addControl("key", new Classic.InputControl("text", { initial }));
    this.addInput("value", new Classic.Input(socket, "Number"));
  }

  data() {
    return {};
  }

  serialize() {
    return {
      key: this.controls.key.value
    };
  }
}
