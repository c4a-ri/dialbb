import type { BaseSchemes, GetSchemes } from 'rete'

export type BSchemes = GetSchemes<
  BaseSchemes['Node'] & { clone?: () => BaseSchemes['Node'] },
  BaseSchemes['Connection']
>
export type NodeFactory<Schemes extends BSchemes> = () => Schemes['Node'] | Promise<Schemes['Node']>

export type ItemDefinition<Schemes extends BSchemes> =
  | [string, NodeFactory<Schemes> | ItemDefinition<Schemes>[]]
