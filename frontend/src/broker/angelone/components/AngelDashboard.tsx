import React, { useEffect, useState } from 'react';
import { useAngelLogin, useAngelOrders, useAngelPositions, useAngelWebSocket } from '../hooks';
import { AngelOrderRequest, AngelCredentials } from '../types';

export const AngelDashboard: React.FC = () => {
  const { isAuthenticated, profile, login, logout, isLoading: authLoading, error: authError } = useAngelLogin();
  const { orders, fetchOrders, placeOrder, cancelOrder, isLoading: ordersLoading } = useAngelOrders();
  const { holdings, positions, funds, fetchAll, isLoading: positionsLoading } = useAngelPositions();
  const { liveTicks, subscribe, unsubscribe } = useAngelWebSocket();

  const [clientCode, setClientCode] = useState('');
  const [password, setPassword] = useState('');
  const [totp, setTotp] = useState('');

  // Sample order state
  const [orderForm, setOrderForm] = useState<Partial<AngelOrderRequest>>({
    variety: 'NORMAL',
    tradingsymbol: '',
    symboltoken: '',
    transactiontype: 'BUY',
    exchange: 'NSE',
    ordertype: 'MARKET',
    producttype: 'INTRADAY',
    duration: 'DAY',
    price: 0,
    quantity: 1
  });

  useEffect(() => {
    if (isAuthenticated) {
      fetchOrders();
      fetchAll();
      // Example subscription for a token
      subscribe(['3045'], 1, 1); // Subscribe to some token
    }
    return () => {
      if (isAuthenticated) {
        unsubscribe(['3045'], 1, 1);
      }
    };
  }, [isAuthenticated, fetchOrders, fetchAll, subscribe, unsubscribe]);

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    login({ 
      client_id: clientCode, 
      mpin: password, 
      totp_token: totp,
      api_key: import.meta.env.VITE_ANGEL_API_KEY || '',
      secret_key: import.meta.env.VITE_ANGEL_SECRET_KEY || ''
    });
  };

  const handlePlaceOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await placeOrder(orderForm as AngelOrderRequest);
      alert('Order placed successfully!');
    } catch (err: any) {
      alert(`Order failed: ${err.message}`);
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="p-6 max-w-md mx-auto bg-white rounded-xl shadow-md space-y-4">
        <h2 className="text-xl font-bold">Angel One Login</h2>
        {authError && <div className="text-red-500 text-sm">{authError}</div>}
        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Client Code</label>
            <input type="text" value={clientCode} onChange={e => setClientCode(e.target.value)} className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2" required />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Password</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2" required />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">TOTP</label>
            <input type="text" value={totp} onChange={e => setTotp(e.target.value)} className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2" required />
          </div>
          <button type="submit" disabled={authLoading} className="w-full bg-blue-600 text-white p-2 rounded-md hover:bg-blue-700 disabled:opacity-50">
            {authLoading ? 'Logging in...' : 'Login'}
          </button>
        </form>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center bg-white p-4 rounded-xl shadow-sm">
        <div>
          <h2 className="text-2xl font-bold">Broker Dashboard</h2>
          <p className="text-sm text-gray-500">Welcome, {profile?.name || profile?.client_code || 'User'}</p>
        </div>
        <div className="flex gap-4 items-center">
          <div className="text-right">
            <p className="text-sm text-gray-500">Available Margin</p>
            <p className="font-bold text-green-600">₹{funds?.availablelimitmargin || '0.00'}</p>
          </div>
          <button onClick={logout} className="bg-red-100 text-red-600 px-4 py-2 rounded hover:bg-red-200">Logout</button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* Left Column: Order Entry */}
        <div className="bg-white p-4 rounded-xl shadow-sm space-y-4">
          <h3 className="font-semibold text-lg">Place Order</h3>
          <form onSubmit={handlePlaceOrder} className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-700">Symbol</label>
              <input type="text" value={orderForm.tradingsymbol} onChange={e => setOrderForm({...orderForm, tradingsymbol: e.target.value})} className="mt-1 block w-full border rounded p-2 text-sm" placeholder="e.g. SBIN-EQ" required />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs font-medium text-gray-700">Token</label>
                <input type="text" value={orderForm.symboltoken} onChange={e => setOrderForm({...orderForm, symboltoken: e.target.value})} className="mt-1 block w-full border rounded p-2 text-sm" placeholder="e.g. 3045" required />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700">Type</label>
                <select value={orderForm.transactiontype} onChange={e => setOrderForm({...orderForm, transactiontype: e.target.value as any})} className="mt-1 block w-full border rounded p-2 text-sm">
                  <option value="BUY">BUY</option>
                  <option value="SELL">SELL</option>
                </select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs font-medium text-gray-700">Quantity</label>
                <input type="number" value={orderForm.quantity} onChange={e => setOrderForm({...orderForm, quantity: Number(e.target.value)})} className="mt-1 block w-full border rounded p-2 text-sm" required min="1" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700">Price</label>
                <input type="number" value={orderForm.price} onChange={e => setOrderForm({...orderForm, price: Number(e.target.value)})} className="mt-1 block w-full border rounded p-2 text-sm" />
              </div>
            </div>
            <button type="submit" disabled={ordersLoading} className="w-full bg-green-600 text-white p-2 rounded hover:bg-green-700 disabled:opacity-50">
              {orderForm.transactiontype === 'BUY' ? 'Buy' : 'Sell'}
            </button>
          </form>
        </div>

        {/* Middle Column: Orders & Positions */}
        <div className="bg-white p-4 rounded-xl shadow-sm md:col-span-2 space-y-6">
          
          {/* Market Feed Quick View */}
          <div>
            <h3 className="font-semibold text-lg mb-2">Live Market Feed</h3>
            <div className="flex gap-4 overflow-x-auto pb-2">
              {Object.values(liveTicks).map(tick => (
                <div key={tick.token} className="border rounded p-3 min-w-[150px]">
                  <p className="text-xs text-gray-500">Token: {tick.token}</p>
                  <p className="font-bold text-lg">{tick.last_traded_price?.toFixed(2) || '---'}</p>
                </div>
              ))}
              {Object.keys(liveTicks).length === 0 && <p className="text-sm text-gray-500">No active subscriptions or data.</p>}
            </div>
          </div>

          <div>
            <h3 className="font-semibold text-lg mb-2">Recent Orders</h3>
            {ordersLoading ? <p className="text-sm">Loading...</p> : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm whitespace-nowrap">
                  <thead>
                    <tr className="bg-gray-50">
                      <th className="p-2">Symbol</th>
                      <th className="p-2">Type</th>
                      <th className="p-2">Status</th>
                      <th className="p-2">Price</th>
                      <th className="p-2">Qty</th>
                      <th className="p-2">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {orders.slice(0, 5).map((order) => (
                      <tr key={order.orderid} className="border-b">
                        <td className="p-2">{order.tradingsymbol}</td>
                        <td className={`p-2 font-medium ${order.transactiontype === 'BUY' ? 'text-green-600' : 'text-red-600'}`}>{order.transactiontype}</td>
                        <td className="p-2">{order.status}</td>
                        <td className="p-2">{order.averageprice || order.price}</td>
                        <td className="p-2">{order.filledshares}/{order.quantity}</td>
                        <td className="p-2">
                          {['open', 'pending'].includes(order.status.toLowerCase()) && (
                            <button onClick={() => cancelOrder(order.orderid, order.variety)} className="text-red-500 hover:underline">Cancel</button>
                          )}
                        </td>
                      </tr>
                    ))}
                    {orders.length === 0 && <tr><td colSpan={6} className="p-4 text-center text-gray-500">No recent orders</td></tr>}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div>
            <h3 className="font-semibold text-lg mb-2">Positions</h3>
            {positionsLoading ? <p className="text-sm">Loading...</p> : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm whitespace-nowrap">
                  <thead>
                    <tr className="bg-gray-50">
                      <th className="p-2">Symbol</th>
                      <th className="p-2">Product</th>
                      <th className="p-2">Net Qty</th>
                      <th className="p-2">Avg Price</th>
                      <th className="p-2">LTP</th>
                      <th className="p-2">P&L</th>
                    </tr>
                  </thead>
                  <tbody>
                    {positions.map((pos) => (
                      <tr key={pos.symboltoken} className="border-b">
                        <td className="p-2">{pos.tradingsymbol}</td>
                        <td className="p-2">{pos.producttype}</td>
                        <td className="p-2">{pos.netqty}</td>
                        <td className="p-2">{pos.netprice}</td>
                        <td className="p-2">{pos.ltp}</td>
                        <td className={`p-2 font-medium ${Number(pos.pnl) >= 0 ? 'text-green-600' : 'text-red-600'}`}>{pos.pnl}</td>
                      </tr>
                    ))}
                    {positions.length === 0 && <tr><td colSpan={6} className="p-4 text-center text-gray-500">No open positions</td></tr>}
                  </tbody>
                </table>
              </div>
            )}
          </div>

        </div>
      </div>
    </div>
  );
};
