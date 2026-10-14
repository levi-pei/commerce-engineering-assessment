import type { OptionName, Product, Selection, Sku } from './types'

export function resolveSku(product: Product, selection: Selection): Sku | null {
  const complete = product.option_dimensions.every(({ name }) => Boolean(selection[name]))
  if (!complete) return null

  return (
    product.skus.find((sku) =>
      product.option_dimensions.every(({ name }) => sku.options[name] === selection[name]),
    ) ?? null
  )
}

export function isOptionSelectable(
  product: Product,
  selection: Selection,
  dimension: OptionName,
  value: string,
): boolean {
  const candidate = { ...selection, [dimension]: value }
  return product.skus.some(
    (sku) =>
      sku.is_available &&
      product.option_dimensions.every(
        ({ name }) => !candidate[name] || sku.options[name] === candidate[name],
      ),
  )
}

export function firstDisplaySku(product: Product, selection: Selection): Sku {
  const selected = resolveSku(product, selection)
  if (selected) return selected

  const partialMatch = product.skus.find((sku) =>
    product.option_dimensions.every(
      ({ name }) => !selection[name] || sku.options[name] === selection[name],
    ),
  )
  return partialMatch ?? product.skus[0]
}

