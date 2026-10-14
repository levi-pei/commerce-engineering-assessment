import { Check, Minus, Plus, RefreshCw, ShoppingBag } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'

import { addCartItem, ApiError, fetchCart, fetchProduct } from './api'
import type { OptionName, Product, Selection } from './types'
import { firstDisplaySku, isOptionSelectable, resolveSku } from './variants'
import './styles.css'

type LoadState = 'loading' | 'ready' | 'error'
type SubmitState = 'idle' | 'submitting' | 'success' | 'error'

function formatPrice(cents: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(cents / 100)
}

function makeIdempotencyKey(): string {
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`
}

export default function App() {
  const [loadState, setLoadState] = useState<LoadState>('loading')
  const [product, setProduct] = useState<Product | null>(null)
  const [selection, setSelection] = useState<Selection>({})
  const [quantity, setQuantity] = useState(1)
  const [cartCount, setCartCount] = useState(0)
  const [submitState, setSubmitState] = useState<SubmitState>('idle')
  const [message, setMessage] = useState('')
  // 重试或切换页面后，请求可能乱序返回；仅允许最新响应更新页面状态。
  const requestVersion = useRef(0)
  // 状态更新是异步的；在 React 渲染禁用按钮前，ref 先阻止重复点击。
  const submitting = useRef(false)

  const load = async () => {
    const version = ++requestVersion.current
    const controller = new AbortController()
    setLoadState('loading')
    setMessage('')
    try {
      const [nextProduct, cart] = await Promise.all([
        fetchProduct(controller.signal),
        fetchCart(controller.signal),
      ])
      // 忽略先前加载尝试的迟到响应。
      if (version !== requestVersion.current) return
      setProduct(nextProduct)
      setCartCount(cart.total_item_count)
      setLoadState('ready')
    } catch (error) {
      if (version !== requestVersion.current || (error instanceof DOMException && error.name === 'AbortError')) return
      setLoadState('error')
    }
  }

  useEffect(() => {
    void load()
    return () => {
      requestVersion.current += 1
    }
  }, [])

  const selectedSku = useMemo(
    () => (product ? resolveSku(product, selection) : null),
    [product, selection],
  )
  const displaySku = useMemo(
    () => (product ? firstDisplaySku(product, selection) : null),
    [product, selection],
  )

  useEffect(() => {
    // 服务端响应后库存可能改变；收紧当前数量，但保留已有的成功或失败提示。
    const maximum = selectedSku?.available_quantity ?? 1
    setQuantity((current) => Math.max(1, Math.min(current, Math.max(1, maximum))))
  }, [selectedSku?.available_quantity])

  useEffect(() => {
    // 切换 SKU 等同于新的购买意图，旧的提交反馈不再适用于当前规格。
    setSubmitState('idle')
    setMessage('')
  }, [selectedSku?.id])

  const chooseOption = (name: OptionName, value: string) => {
    setSelection((current) => ({ ...current, [name]: value }))
  }

  const updateSelectedStock = (availableQuantity: number) => {
    if (!selectedSku) return
    setProduct((current) =>
      current
        ? {
            ...current,
            skus: current.skus.map((sku) =>
              sku.id === selectedSku.id ? { ...sku, available_quantity: availableQuantity } : sku,
            ),
          }
        : current,
    )
  }

  const handleAdd = async () => {
    if (!selectedSku || !selectedSku.is_available || selectedSku.available_quantity < quantity || submitting.current) return
    submitting.current = true
    setSubmitState('submitting')
    setMessage('Adding item to cart.')
    try {
      // 每次用户意图生成一个键；网络重试时后端会重放同一结果。
      const result = await addCartItem(selectedSku.id, quantity, makeIdempotencyKey())
      updateSelectedStock(result.available_quantity)
      setCartCount(result.cart_total_item_count)
      setSubmitState('success')
      setMessage(`${quantity} item${quantity === 1 ? '' : 's'} added to your cart.`)
    } catch (error) {
      if (error instanceof ApiError && error.code === 'INSUFFICIENT_STOCK') {
        const latestStock = Number(error.details.available_quantity)
        if (Number.isFinite(latestStock)) updateSelectedStock(latestStock)
      }
      setSubmitState('error')
      setMessage(error instanceof Error ? error.message : 'Unable to add this item. Please try again.')
    } finally {
      submitting.current = false
    }
  }

  if (loadState === 'loading') {
    return (
      <main className="status-page" aria-busy="true">
        <div className="spinner" aria-hidden="true" />
        <p>Loading product</p>
      </main>
    )
  }

  if (loadState === 'error' || !product || !displaySku) {
    return (
      <main className="status-page">
        <p className="eyebrow">Fieldwork Supply</p>
        <h1>We couldn't load this product.</h1>
        <button className="secondary-button" onClick={() => void load()}>
          <RefreshCw size={18} aria-hidden="true" /> Retry
        </button>
      </main>
    )
  }

  const selectionComplete = product.option_dimensions.every(({ name }) => selection[name])
  const unavailableCombination = selectionComplete && !selectedSku
  const outOfStock = Boolean(selectedSku && selectedSku.available_quantity === 0)
  const unavailable = Boolean(selectedSku && !selectedSku.is_available)
  const canAdd = Boolean(selectedSku && selectedSku.is_available && selectedSku.available_quantity >= quantity)

  let stockLabel = 'Select options to see availability'
  if (unavailableCombination || unavailable) stockLabel = 'This combination is unavailable'
  else if (outOfStock) stockLabel = 'Out of stock'
  else if (selectedSku && selectedSku.available_quantity <= 3) stockLabel = `Only ${selectedSku.available_quantity} left`
  else if (selectedSku) stockLabel = 'In stock'

  return (
    <div className="app-shell">
      <header className="site-header">
        <a className="brand" href="/" aria-label="Fieldwork Supply home">FIELDWORK</a>
        <div className="cart-indicator" aria-label={`${cartCount} items in cart`}>
          <ShoppingBag size={20} aria-hidden="true" />
          <span>{cartCount}</span>
        </div>
      </header>

      <main className="product-layout">
        <section className="product-media" aria-label="Product image">
          <img src={displaySku.image_url} alt={`${product.name} in ${displaySku.options.colour}`} />
          <span className="media-index">01 / 02</span>
        </section>

        <section className="product-details">
          <p className="eyebrow">Weather-ready workwear</p>
          <h1>{product.name}</h1>
          <p className="price">{formatPrice(displaySku.price_cents)}</p>
          <p className="description">{product.description}</p>

          <div className="option-groups">
            {product.option_dimensions.map((dimension) => (
              <fieldset key={dimension.name}>
                <legend>
                  {dimension.label}
                  <span>{selection[dimension.name] ?? 'Not selected'}</span>
                </legend>
                <div className={`option-list option-list--${dimension.name}`}>
                  {dimension.values.map((value) => {
                    const selectable = isOptionSelectable(product, selection, dimension.name, value)
                    const selected = selection[dimension.name] === value
                    return (
                      <button
                        key={value}
                        type="button"
                        className="option-button"
                        aria-pressed={selected}
                        disabled={!selectable}
                        onClick={() => chooseOption(dimension.name, value)}
                      >
                        {dimension.name === 'colour' && (
                          <span className={`swatch swatch--${value === 'Graphite' ? 'graphite' : 'red'}`} aria-hidden="true" />
                        )}
                        {value}
                        {selected && <Check size={16} aria-hidden="true" />}
                      </button>
                    )
                  })}
                </div>
              </fieldset>
            ))}
          </div>

          <div className="purchase-row">
            <div className="quantity-control" aria-label="Quantity selector">
              <button
                type="button"
                aria-label="Decrease quantity"
                disabled={quantity <= 1}
                onClick={() => setQuantity((current) => Math.max(1, current - 1))}
              >
                <Minus size={17} aria-hidden="true" />
              </button>
              <output aria-label="Quantity">{quantity}</output>
              <button
                type="button"
                aria-label="Increase quantity"
                disabled={!selectedSku || quantity >= selectedSku.available_quantity}
                onClick={() => setQuantity((current) => current + 1)}
              >
                <Plus size={17} aria-hidden="true" />
              </button>
            </div>
            <button
              type="button"
              className="add-button"
              disabled={!canAdd || submitState === 'submitting'}
              onClick={() => void handleAdd()}
            >
              {submitState === 'submitting' ? 'Adding...' : 'Add to cart'}
            </button>
          </div>

          <p className={`stock-status ${outOfStock || unavailableCombination ? 'stock-status--alert' : ''}`}>
            <span aria-hidden="true" /> {stockLabel}
          </p>
          <div className={`feedback feedback--${submitState}`} aria-live="polite" aria-atomic="true">
            {message}
          </div>

          <dl className="product-notes">
            <div><dt>Material</dt><dd>68% recycled nylon</dd></div>
            <div><dt>Fit</dt><dd>Relaxed utility cut</dd></div>
            <div><dt>Dispatch</dt><dd>Within 2 business days</dd></div>
          </dl>
        </section>
      </main>
    </div>
  )
}
