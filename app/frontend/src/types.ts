export type OptionName = 'colour' | 'size'

export interface OptionDimension {
  name: OptionName
  label: string
  values: string[]
}

export interface Sku {
  id: string
  price_cents: number
  available_quantity: number
  is_available: boolean
  image_url: string
  options: Record<OptionName, string>
}

export interface Product {
  id: string
  name: string
  description: string
  option_dimensions: OptionDimension[]
  skus: Sku[]
}

export type Selection = Partial<Record<OptionName, string>>

export interface Cart {
  items: Array<{
    sku_id: string
    quantity: number
    price_cents: number
    colour: string
    size: string
  }>
  total_item_count: number
  subtotal_cents: number
}

export interface AddCartResult {
  sku_id: string
  added_quantity: number
  available_quantity: number
  cart_total_item_count: number
}

export interface ApiErrorBody {
  error: {
    code: string
    message: string
    details: Record<string, unknown>
  }
}

