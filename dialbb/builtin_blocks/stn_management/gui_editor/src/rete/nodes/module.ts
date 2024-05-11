import { ClassicPreset as Classic, NodeEditor } from "rete";
import type { DataflowNode } from "rete-engine";
import { socket } from "../sockets";
import type { Module } from "../modules";
import { Modules } from "../modules";
import type { Schemes } from "../editor";

export class ModuleNode
  extends Classic.Node<
    Record<string, Classic.Socket>,
    Record<string, Classic.Socket>,
    { module: Classic.InputControl<"text"> }
  >
  implements DataflowNode {
  width = 180;
  height = 140;
  module: null | Module<Schemes> = null;

  constructor(
    public path: string,
    private findModule: (path: string) => null | Module<Schemes>,
    private reset: (nodeId: string) => Promise<void>,
    updateUI: (nodeId: string) => void
  ) {
    super("Module");

    this.addControl(
      "module",
      new Classic.InputControl("text", {
        initial: path,
        change: async (value) => {
          this.path = value;
          await this.update();
          updateUI(this.id);
        }
      })
    );
    this.update();
  }

  async update() {
    this.module = this.findModule(this.path);

    await this.reset(this.id);
    if (this.module) {
      const editor = new NodeEditor<Schemes>();
      await this.module.apply(editor);

      const { inputs, outputs } = Modules.getPorts(editor);
      this.syncPorts(inputs, outputs);
    } else this.syncPorts([], []);
  }

  syncPorts(inputs: string[], outputs: string[]) {
    Object.keys(this.inputs).forEach((key: keyof typeof this.inputs) =>
      this.removeInput(key)
    );
    Object.keys(this.outputs).forEach((key: keyof typeof this.outputs) =>
      this.removeOutput(key)
    );

    inputs.forEach((key) => {
      this.addInput(key, new Classic.Input(socket, key));
    });
    outputs.forEach((key) => {
      this.addOutput(key, new Classic.Output(socket, key));
    });
    this.height =
      110 +
      25 * (Object.keys(this.inputs).length + Object.keys(this.outputs).length);
  }

  async data(inputs: Record<string, any>) {
    const data = await this.module?.exec(inputs);

    return data || {};
  }

  serialize() {
    return {
      name: this.controls.module.value
    };
  }
}
