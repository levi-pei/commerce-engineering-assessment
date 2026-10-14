import type { AddCartResult, ApiErrorBody, Cart, Product } from './types'

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code: string,
    readonly details: Record<string, unknown>,
  ) {
    super(message)
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init)
  const body = (await response.json()) as T | ApiErrorBody
  if (!response.ok) {
    const apiError = body as ApiErrorBody
    throw new ApiError(
      apiError.error?.message ?? 'The request failed.',
      response.status,
      apiError.error?.code ?? 'UNKNOWN_ERROR',
      apiError.error?.details ?? {},
    )
  }
  return body as T
}

export function fetchProduct(signal?: AbortSignal): Promise<Product> {
  return request('/api/products/everyday-shell', { signal })
}

export function fetchCart(signal?: AbortSignal): Promise<Cart> {
  return request('/api/cart', { signal })
}

export function addCartItem(
  skuId: string,
  quantity: number,
  idempotencyKey: string,
): Promise<AddCartResult> {
  return request('/api/cart/items', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Idempotency-Key': idempotencyKey,
    },
    body: JSON.stringify({ sku_id: skuId, quantity }),
  })
}

