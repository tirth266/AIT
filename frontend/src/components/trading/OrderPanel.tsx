import { useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  ArrowUpDown, TrendingUp, TrendingDown, 
  AlertTriangle, Check, X, Zap, Clock
} from 'lucide-react'
import { clsx } from 'clsx'
import { useTradingEngineStore } from '../../store'
import type { MarketQuote, OrderType, TransactionType, ProductType } from '../../types'

interface OrderPanelProps {
  symbol: string
  quote?: MarketQuote | null
  onOrderPlaced?: (order: unknown) => void
}

const ORDER_TYPES: { value: OrderType; label: string; description: string }[] = [
  { value: 'MARKET', label: 'Market', description: 'Execute immediately at best price' },
  { value: 'LIMIT', label: 'Limit', description: 'Execute at specific price' },
  { value: 'SL', label: 'SL', description: 'Stop Loss' },
  { value: 'SL-M', label: 'SL-M', description: 'Stop Loss Market' },
]

const PRODUCT_TYPES: { value: ProductType; label: string; description: string }[] = [
  { value: 'MIS', label: 'MIS', description: 'Intraday' },
  { value: 'CNC', label: 'CNC', description: 'Delivery' },
  { value: 'NRML', label: 'NRML', description: 'Carry Forward' },
]

export function OrderPanel({ symbol, quote, onOrderPlaced }: OrderPanelProps) {
  const { createOrder, isSubmittingOrder, error, margin } = useTradingEngineStore()
  
  const [side, setSide] = useState<TransactionType>('BUY')
  const [orderType, setOrderType] = useState<OrderType>('MARKET')
  const [productType, setProductType] = useState<ProductType>('MIS')
  const [quantity, setQuantity] = useState<number>(1)
  const [price, setPrice] = useState<string>('')
  const [triggerPrice, setTriggerPrice] = useState<string>('')
  const [showConfirmation, setShowConfirmation] = useState(false)
  const [orderSuccess, setOrderSuccess] = useState(false)
  
  const currentPrice = quote?.last_price || 0
  const bidPrice = quote?.bid || currentPrice * 0.999
  const askPrice = quote?.ask || currentPrice * 1.001
  
  const selectedPrice = orderType === 'MARKET' ? (side === 'BUY' ? askPrice : bidPrice) : parseFloat(price) || currentPrice
  const totalValue = quantity * selectedPrice
  
  const estimatedBrokerage = totalValue * 0.00003
  const estimatedGST = estimatedBrokerage * 0.18
  const estimatedSTT = side === 'SELL' ? totalValue * 0.00125 : totalValue * 0.00025
  const totalCharges = estimatedBrokerage + estimatedGST + estimatedSTT
  
  const handlePlaceOrder = useCallback(async () => {
    setShowConfirmation(true)
  }, [])
  
  const confirmOrder = useCallback(async () => {
    const order = await createOrder({
      symbol,
      transaction_type: side,
      order_type: orderType,
      quantity,
      price: orderType !== 'MARKET' ? parseFloat(price) || undefined : undefined,
      trigger_price: ['SL', 'SL-M'].includes(orderType) ? parseFloat(triggerPrice) || undefined : undefined,
      product_type: productType,
      mode: 'paper',
    })
    
    if (order) {
      setOrderSuccess(true)
      setTimeout(() => {
        setOrderSuccess(false)
        setShowConfirmation(false)
        setQuantity(1)
        setPrice('')
        setTriggerPrice('')
      }, 2000)
      onOrderPlaced?.(order)
    } else {
      setShowConfirmation(false)
    }
  }, [createOrder, symbol, side, orderType, quantity, price, triggerPrice, productType, onOrderPlaced])
  
  const quickTrade = useCallback((qty: number) => {
    setQuantity(qty)
  }, [])
  
  return (
    <div className="bg-card border border-border rounded-xl p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-lg">{symbol}</h3>
          {quote && (
            <span className="text-2xl font-bold text-foreground">
              {quote.last_price.toFixed(2)}
            </span>
          )}
        </div>
        {margin && (
          <div className="text-sm text-muted-foreground">
            <span className="font-medium text-foreground">₹{margin.available_margin.toLocaleString()}</span> available
          </div>
        )}
      </div>
      
      <div className="flex gap-2 p-1 bg-muted rounded-lg">
        <button
          onClick={() => setSide('BUY')}
          className={clsx(
            'flex-1 py-2 rounded-md font-medium transition-all',
            side === 'BUY' 
              ? 'bg-green-600 text-white shadow-md' 
              : 'text-muted-foreground hover:bg-muted/50'
          )}
        >
          BUY
        </button>
        <button
          onClick={() => setSide('SELL')}
          className={clsx(
            'flex-1 py-2 rounded-md font-medium transition-all',
            side === 'SELL' 
              ? 'bg-red-600 text-white shadow-md' 
              : 'text-muted-foreground hover:bg-muted/50'
          )}
        >
          SELL
        </button>
      </div>
      
      <div className="space-y-2">
        <label className="text-sm font-medium text-muted-foreground">Order Type</label>
        <div className="grid grid-cols-4 gap-1">
          {ORDER_TYPES.map((type) => (
            <button
              key={type.value}
              onClick={() => setOrderType(type.value)}
              className={clsx(
                'py-2 px-2 text-xs font-medium rounded-md transition-all',
                orderType === type.value
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground hover:bg-muted/70'
              )}
            >
              {type.label}
            </button>
          ))}
        </div>
      </div>
      
      <div className="space-y-2">
        <label className="text-sm font-medium text-muted-foreground">Product Type</label>
        <div className="grid grid-cols-3 gap-1">
          {PRODUCT_TYPES.map((type) => (
            <button
              key={type.value}
              onClick={() => setProductType(type.value)}
              className={clsx(
                'py-2 text-xs font-medium rounded-md transition-all',
                productType === type.value
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground hover:bg-muted/70'
              )}
            >
              {type.label}
            </button>
          ))}
        </div>
      </div>
      
      <div className="grid grid-cols-3 gap-2">
        <div className="space-y-1">
          <label className="text-xs text-muted-foreground">Qty</label>
          <input
            type="number"
            value={quantity}
            onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
            className="w-full px-3 py-2 bg-muted border border-border rounded-md text-center font-mono text-lg"
            min={1}
          />
        </div>
        
        {orderType !== 'MARKET' && (
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">Price</label>
            <input
              type="number"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              placeholder={currentPrice.toFixed(2)}
              className="w-full px-3 py-2 bg-muted border border-border rounded-md text-center font-mono"
              step={0.05}
            />
          </div>
        )}
        
        {['SL', 'SL-M'].includes(orderType) && (
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">Trigger</label>
            <input
              type="number"
              value={triggerPrice}
              onChange={(e) => setTriggerPrice(e.target.value)}
              placeholder={currentPrice.toFixed(2)}
              className="w-full px-3 py-2 bg-muted border border-border rounded-md text-center font-mono"
              step={0.05}
            />
          </div>
        )}
      </div>
      
      <div className="flex gap-1">
        {[1, 5, 10, 25, 50, 100].map((qty) => (
          <button
            key={qty}
            onClick={() => quickTrade(qty)}
            className="flex-1 py-1 text-xs bg-muted hover:bg-muted/70 rounded transition-colors"
          >
            {qty}
          </button>
        ))}
      </div>
      
      <div className="space-y-2 text-sm">
        <div className="flex justify-between text-muted-foreground">
          <span>Order Value</span>
          <span className="font-medium text-foreground">₹{totalValue.toFixed(2)}</span>
        </div>
        <div className="flex justify-between text-muted-foreground">
          <span>Est. Brokerage</span>
          <span>₹{estimatedBrokerage.toFixed(2)}</span>
        </div>
        <div className="flex justify-between text-muted-foreground">
          <span>Est. Taxes</span>
          <span>₹{(estimatedGST + estimatedSTT).toFixed(2)}</span>
        </div>
        <div className="flex justify-between text-muted-foreground">
          <span>Total Charges</span>
          <span>₹{totalCharges.toFixed(2)}</span>
        </div>
        <div className="flex justify-between font-medium text-foreground border-t pt-2">
          <span>Net Value</span>
          <span>₹{(totalValue + totalCharges).toFixed(2)}</span>
        </div>
      </div>
      
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-sm text-red-400"
          >
            <AlertTriangle className="w-4 h-4" />
            {error}
          </motion.div>
        )}
      </AnimatePresence>
      
      <motion.button
        onClick={handlePlaceOrder}
        disabled={isSubmittingOrder || !symbol}
        whileTap={{ scale: 0.98 }}
        className={clsx(
          'w-full py-4 rounded-lg font-bold text-lg transition-all',
          side === 'BUY'
            ? 'bg-green-600 hover:bg-green-700 text-white'
            : 'bg-red-600 hover:bg-red-700 text-white',
          'disabled:opacity-50 disabled:cursor-not-allowed'
        )}
      >
        {isSubmittingOrder ? (
          <span className="flex items-center justify-center gap-2">
            <Clock className="w-5 h-5 animate-spin" />
            Processing...
          </span>
        ) : orderSuccess ? (
          <span className="flex items-center justify-center gap-2">
            <Check className="w-5 h-5" />
            Order Placed!
          </span>
        ) : (
          <span className="flex items-center justify-center gap-2">
            <Zap className="w-5 h-5" />
            {side === 'BUY' ? 'BUY' : 'SELL'} {quantity} @ {selectedPrice.toFixed(2)}
          </span>
        )}
      </motion.button>
      
      <AnimatePresence>
        {showConfirmation && !orderSuccess && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
            onClick={() => setShowConfirmation(false)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-card border border-border rounded-xl p-6 w-96 max-w-[90vw]"
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="text-lg font-semibold mb-4">Confirm Order</h3>
              
              <div className="space-y-3 mb-6">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Symbol</span>
                  <span className="font-medium">{symbol}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Type</span>
                  <span className={clsx(
                    'font-medium',
                    side === 'BUY' ? 'text-green-400' : 'text-red-400'
                  )}>
                    {side} {orderType}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Quantity</span>
                  <span className="font-medium">{quantity}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Price</span>
                  <span className="font-medium">₹{selectedPrice.toFixed(2)}</span>
                </div>
                <div className="flex justify-between border-t pt-2">
                  <span className="text-muted-foreground">Total</span>
                  <span className="font-bold">₹{(totalValue + totalCharges).toFixed(2)}</span>
                </div>
              </div>
              
              <div className="flex gap-3">
                <button
                  onClick={() => setShowConfirmation(false)}
                  className="flex-1 py-3 bg-muted hover:bg-muted/70 rounded-lg font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={confirmOrder}
                  disabled={isSubmittingOrder}
                  className={clsx(
                    'flex-1 py-3 rounded-lg font-medium transition-colors',
                    side === 'BUY' 
                      ? 'bg-green-600 hover:bg-green-700 text-white' 
                      : 'bg-red-600 hover:bg-red-700 text-white',
                    'disabled:opacity-50'
                  )}
                >
                  {isSubmittingOrder ? 'Placing...' : 'Confirm'}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default OrderPanel