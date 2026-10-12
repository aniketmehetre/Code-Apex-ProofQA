import React, { useEffect, useState } from "react";
import { api } from "./api";
import { Cart, Order, Product, User } from "./types";

export function App() {
  const [view, setView] = useState<"products" | "cart" | "checkout" | "orders" | "about" | "auth">("products");
  const [products, setProducts] = useState<Product[]>([]);
  const [totalProducts, setTotalProducts] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [category, setCategory] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [sortOrder, setSortOrder] = useState<string>("");
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);

  const [cart, setCart] = useState<Cart>({
    items: [],
    item_count: 0,
    subtotal: 0,
    discount: 0,
    total: 0,
    applied_coupon: null,
  });

  const [couponCode, setCouponCode] = useState<string>("");
  const [couponMessage, setCouponMessage] = useState<string | null>(null);
  const [couponError, setCouponError] = useState<string | null>(null);

  const [address, setAddress] = useState<string>("");
  const [orders, setOrders] = useState<Order[]>([]);
  const [lastPlacedOrder, setLastPlacedOrder] = useState<Order | null>(null);

  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [authEmail, setAuthEmail] = useState<string>("");
  const [authPassword, setAuthPassword] = useState<string>("");
  const [authName, setAuthName] = useState<string>("");
  const [authError, setAuthError] = useState<string | null>(null);

  const [notification, setNotification] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setNotification(msg);
    setTimeout(() => setNotification(null), 3000);
  };

  // Load Cart and Initial Data
  const fetchCartData = async () => {
    try {
      const c = await api.getCart();
      setCart(c);
    } catch {
      // Ignore initial session errors
    }
  };

  const fetchProducts = async () => {
    try {
      const data = await api.getProducts({
        q: searchQuery,
        category: category,
        sort: sortOrder,
        page: page,
        page_size: 12,
      });
      setProducts(data.products);
      setTotalProducts(data.total);
      setTotalPages(data.total_pages);
    } catch (err: any) {
      console.error("Failed to load products", err);
    }
  };

  useEffect(() => {
    fetchProducts();
  }, [category, sortOrder, page]);

  useEffect(() => {
    fetchCartData();
  }, []);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchProducts();
  };

  const handleAddToCart = async (product: Product, qty: number = 1) => {
    try {
      const updated = await api.addToCart(product.id, qty);
      setCart(updated);
      showToast(`Added "${product.name}" to cart`);
      if (selectedProduct) setSelectedProduct(null);
    } catch (err: any) {
      alert(`Could not add to cart: ${err.message}`);
    }
  };

  const handleUpdateQty = async (itemId: number, newQty: number) => {
    try {
      const updated = await api.updateCartItem(itemId, newQty);
      setCart(updated);
    } catch (err: any) {
      alert(`Error updating quantity: ${err.message}`);
    }
  };

  const handleRemoveCartItem = async (itemId: number) => {
    try {
      const updated = await api.removeCartItem(itemId);
      setCart(updated);
      showToast("Removed item from cart");
    } catch (err: any) {
      alert(`Error removing item: ${err.message}`);
    }
  };

  const handleApplyCoupon = async (e: React.FormEvent) => {
    e.preventDefault();
    setCouponMessage(null);
    setCouponError(null);
    try {
      const res = await api.applyCoupon(couponCode);
      setCouponMessage(`Applied ${res.coupon} (-${res.discount_percent}%)`);
      await fetchCartData();
    } catch (err: any) {
      setCouponError(err.message);
    }
  };

  const handleCheckoutSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!address.trim()) {
      alert("Please provide a valid shipping address");
      return;
    }
    try {
      const res = await api.checkout(address);
      setLastPlacedOrder(res.order);
      await fetchCartData();
      setView("orders");
      await loadOrders();
      showToast("Order successfully placed!");
    } catch (err: any) {
      alert(`Checkout failed: ${err.message}`);
    }
  };

  const loadOrders = async () => {
    try {
      const list = await api.getOrders();
      setOrders(list);
    } catch (err) {
      console.error(err);
    }
  };

  const handleAuthSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError(null);
    try {
      if (authMode === "register") {
        const res = await api.register(authEmail, authPassword, authName);
        setCurrentUser(res.user);
        showToast(`Registered successfully as ${res.user.name}`);
      } else {
        const res = await api.login(authEmail, authPassword);
        setCurrentUser(res.user);
        showToast(`Logged in as ${res.user.name}`);
      }
      setView("products");
    } catch (err: any) {
      setAuthError(err.message);
    }
  };

  const handleLogout = async () => {
    await api.logout();
    setCurrentUser(null);
    showToast("Logged out");
  };

  return (
    <div>
      {/* Toast Notification */}
      {notification && (
        <div
          style={{
            position: "fixed",
            bottom: "2rem",
            right: "2rem",
            backgroundColor: "var(--accent-green)",
            color: "#000",
            padding: "0.8rem 1.4rem",
            borderRadius: "var(--radius-md)",
            fontWeight: 600,
            zIndex: 100,
            boxShadow: "var(--shadow-lg)",
          }}
        >
          {notification}
        </div>
      )}

      {/* Header */}
      <header className="site-header" role="banner">
        <div className="container header-inner">
          <div className="logo-badge" style={{ cursor: "pointer" }} onClick={() => setView("products")}>
            <div className="logo-icon">P</div>
            <span>ApexShop Twin</span>
          </div>

          <nav className="nav-links" role="navigation" aria-label="Main Navigation">
            <button
              className={`nav-link ${view === "products" ? "active" : ""}`}
              onClick={() => setView("products")}
            >
              Shop
            </button>
            <button
              className={`nav-link ${view === "about" ? "active" : ""}`}
              onClick={() => setView("about")}
            >
              About
            </button>
            <button
              className={`nav-link ${view === "orders" ? "active" : ""}`}
              onClick={() => {
                setView("orders");
                loadOrders();
              }}
            >
              Orders
            </button>
            {currentUser ? (
              <button className="nav-link" onClick={handleLogout}>
                Logout ({currentUser.name})
              </button>
            ) : (
              <button
                className={`nav-link ${view === "auth" ? "active" : ""}`}
                onClick={() => setView("auth")}
              >
                Sign In
              </button>
            )}

            <button
              className="cart-button"
              onClick={() => setView("cart")}
              aria-label="View Shopping Cart"
            >
              <span>Cart</span>
              <span className="cart-badge" data-testid="cart-badge">
                {cart.item_count}
              </span>
            </button>
          </nav>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="container" role="main" style={{ paddingBottom: "4rem" }}>
        {/* VIEW: PRODUCTS */}
        {view === "products" && (
          <div>
            {/* Filter and Search Bar */}
            <div className="filter-bar" role="search">
              <form onSubmit={handleSearchSubmit} style={{ display: "flex", flex: 1, gap: "0.5rem" }}>
                <input
                  type="search"
                  className="search-input"
                  placeholder="Search products by title or description..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  aria-label="Search products"
                />
                <button type="submit" className="btn-primary" aria-label="Submit Search">
                  Search
                </button>
              </form>

              <div className="filter-group">
                <select
                  className="select-control"
                  value={category}
                  onChange={(e) => {
                    setCategory(e.target.value);
                    setPage(1);
                  }}
                  aria-label="Filter by Category"
                >
                  <option value="">All Categories</option>
                  <option value="Electronics">Electronics</option>
                  <option value="Clothing">Clothing</option>
                  <option value="Books">Books</option>
                  <option value="Home">Home</option>
                </select>

                <select
                  className="select-control"
                  value={sortOrder}
                  onChange={(e) => {
                    setSortOrder(e.target.value);
                    setPage(1);
                  }}
                  aria-label="Sort products"
                >
                  <option value="">Sort by: Default</option>
                  <option value="price_asc">Price: Low to High</option>
                  <option value="price_desc">Price: High to Low</option>
                  <option value="name">Name: Alphabetical</option>
                </select>
              </div>
            </div>

            {/* Product Count Header */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
              <h2 style={{ fontSize: "1.25rem", fontWeight: 600 }}>Products Catalog</h2>
              <span
                data-testid="product-count"
                style={{ fontSize: "0.9rem", color: "var(--text-secondary)" }}
              >
                Showing {products.length} of {totalProducts} items
              </span>
            </div>

            {/* Grid */}
            <div className="products-grid">
              {products.map((p) => (
                <article key={p.id} className="product-card">
                  <div>
                    <span className="product-category-tag">{p.category}</span>
                    <h3
                      className="product-title"
                      style={{ cursor: "pointer" }}
                      onClick={() => setSelectedProduct(p)}
                    >
                      {p.name}
                    </h3>
                    <p className="product-desc">{p.description}</p>
                  </div>
                  <div className="product-footer">
                    <span className="product-price">${p.price.toFixed(2)}</span>
                    <button
                      className="btn-primary"
                      data-testid={`add-to-cart-${p.id}`}
                      onClick={() => handleAddToCart(p, 1)}
                      aria-label={`Add ${p.name} to cart`}
                    >
                      Add to Cart
                    </button>
                  </div>
                </article>
              ))}
            </div>

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div className="pagination" role="navigation" aria-label="Pagination">
                <button
                  className="page-btn"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  aria-label="Previous Page"
                >
                  &larr; Previous
                </button>
                {Array.from({ length: totalPages }, (_, i) => i + 1).map((num) => (
                  <button
                    key={num}
                    className={`page-btn ${page === num ? "active" : ""}`}
                    onClick={() => setPage(num)}
                    aria-label={`Page ${num}`}
                  >
                    {num}
                  </button>
                ))}
                <button
                  className="page-btn"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  aria-label="Next Page"
                >
                  Next &rarr;
                </button>
              </div>
            )}
          </div>
        )}

        {/* MODAL: PRODUCT DETAIL */}
        {selectedProduct && (
          <div
            style={{
              position: "fixed",
              inset: 0,
              backgroundColor: "rgba(0,0,0,0.7)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              zIndex: 100,
              padding: "1rem",
            }}
          >
            <div
              className="form-card"
              style={{ maxWidth: "600px", width: "100%", margin: 0 }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
                <span className="product-category-tag">{selectedProduct.category}</span>
                <button
                  style={{ color: "var(--text-secondary)", fontSize: "1.25rem" }}
                  onClick={() => setSelectedProduct(null)}
                  aria-label="Close Product Details"
                >
                  &times;
                </button>
              </div>
              <h2 style={{ fontSize: "1.4rem", fontWeight: 700, marginBottom: "0.75rem" }}>
                {selectedProduct.name}
              </h2>
              <p style={{ color: "var(--text-secondary)", marginBottom: "1.5rem" }}>
                {selectedProduct.description}
              </p>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span className="product-price" style={{ fontSize: "1.5rem" }}>
                  ${selectedProduct.price.toFixed(2)}
                </span>
                <button
                  className="btn-primary"
                  onClick={() => handleAddToCart(selectedProduct, 1)}
                  aria-label={`Add ${selectedProduct.name} to cart`}
                >
                  Add to Cart
                </button>
              </div>
            </div>
          </div>
        )}

        {/* VIEW: CART */}
        {view === "cart" && (
          <div>
            <h1 style={{ fontSize: "1.75rem", fontWeight: 700, margin: "2rem 0 1rem 0" }}>
              Shopping Cart
            </h1>

            {cart.items.length === 0 ? (
              <div style={{ padding: "3rem", textAlign: "center", backgroundColor: "var(--bg-surface)", borderRadius: "var(--radius-lg)" }}>
                <p style={{ color: "var(--text-secondary)", marginBottom: "1.5rem", fontSize: "1.1rem" }}>
                  Your cart is currently empty.
                </p>
                <button className="btn-primary" onClick={() => setView("products")}>
                  Browse Products
                </button>
              </div>
            ) : (
              <div className="cart-container">
                <div>
                  <table className="cart-table">
                    <thead>
                      <tr>
                        <th>Product</th>
                        <th>Price</th>
                        <th>Quantity</th>
                        <th>Subtotal</th>
                        <th>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {cart.items.map((it) => (
                        <tr key={it.id}>
                          <td>
                            <strong style={{ display: "block" }}>{it.name}</strong>
                            <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                              {it.category}
                            </span>
                          </td>
                          <td>${it.price.toFixed(2)}</td>
                          <td>
                            <div className="qty-control">
                              <button
                                className="qty-btn"
                                onClick={() => handleUpdateQty(it.id, Math.max(0, it.quantity - 1))}
                                aria-label="Decrease Quantity"
                              >
                                -
                              </button>
                              <span style={{ fontWeight: 600, minWidth: "1.5rem", textAlign: "center" }}>
                                {it.quantity}
                              </span>
                              <button
                                className="qty-btn"
                                onClick={() => handleUpdateQty(it.id, it.quantity + 1)}
                                aria-label="Increase Quantity"
                              >
                                +
                              </button>
                            </div>
                          </td>
                          <td style={{ fontWeight: 600 }}>${it.line_total.toFixed(2)}</td>
                          <td>
                            <button
                              className="btn-danger"
                              onClick={() => handleRemoveCartItem(it.id)}
                              aria-label={`Remove ${it.name} from cart`}
                            >
                              Remove
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="order-summary-card">
                  <h3 style={{ fontSize: "1.2rem", fontWeight: 700, marginBottom: "1rem" }}>
                    Order Summary
                  </h3>

                  <div className="summary-row">
                    <span>Items Count:</span>
                    <span>{cart.item_count}</span>
                  </div>

                  <div className="summary-row">
                    <span>Subtotal:</span>
                    <span>${cart.subtotal.toFixed(2)}</span>
                  </div>

                  {cart.discount > 0 && (
                    <div className="summary-row" style={{ color: "var(--accent-green)" }}>
                      <span>Discount ({cart.applied_coupon}):</span>
                      <span>-${cart.discount.toFixed(2)}</span>
                    </div>
                  )}

                  <div className="summary-row total-row">
                    <span>Total:</span>
                    <span data-testid="cart-total">${cart.total.toFixed(2)}</span>
                  </div>

                  {/* Coupon Box */}
                  <form onSubmit={handleApplyCoupon} className="coupon-box">
                    <input
                      type="text"
                      className="form-input"
                      style={{ flex: 1, textTransform: "uppercase" }}
                      placeholder="Coupon (e.g. SAVE10)"
                      value={couponCode}
                      onChange={(e) => setCouponCode(e.target.value)}
                      aria-label="Coupon Code"
                    />
                    <button type="submit" className="btn-secondary" aria-label="Apply Coupon">
                      Apply
                    </button>
                  </form>
                  {couponMessage && <div className="alert-box alert-success">{couponMessage}</div>}
                  {couponError && <div className="alert-box alert-error">{couponError}</div>}

                  <button
                    className="btn-primary"
                    style={{ width: "100%", marginTop: "1rem", padding: "0.8rem" }}
                    onClick={() => setView("checkout")}
                    aria-label="Proceed to Checkout"
                  >
                    Proceed to Checkout
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* VIEW: CHECKOUT */}
        {view === "checkout" && (
          <div className="form-card">
            <h1 className="form-title">Shipping & Checkout</h1>

            <div style={{ marginBottom: "1.5rem", padding: "1rem", backgroundColor: "var(--bg-card)", borderRadius: "var(--radius-md)" }}>
              <div className="summary-row">
                <span>Items in Order:</span>
                <span>{cart.item_count}</span>
              </div>
              <div className="summary-row" style={{ fontWeight: 700, color: "var(--text-primary)" }}>
                <span>Order Total:</span>
                <span data-testid="cart-total">${cart.total.toFixed(2)}</span>
              </div>
            </div>

            <form onSubmit={handleCheckoutSubmit}>
              <div className="form-group">
                <label className="form-label" htmlFor="address-input">
                  Shipping Address
                </label>
                <textarea
                  id="address-input"
                  className="form-input"
                  rows={3}
                  required
                  placeholder="Enter full shipping street address, suite, city, postal code"
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  aria-label="Shipping Address"
                />
              </div>

              <div style={{ display: "flex", gap: "1rem", marginTop: "1.5rem" }}>
                <button
                  type="button"
                  className="btn-secondary"
                  style={{ flex: 1 }}
                  onClick={() => setView("cart")}
                >
                  Back to Cart
                </button>
                <button
                  type="submit"
                  className="btn-primary"
                  style={{ flex: 1 }}
                  aria-label="Place Order"
                >
                  Place Order
                </button>
              </div>
            </form>
          </div>
        )}

        {/* VIEW: ORDERS */}
        {view === "orders" && (
          <div style={{ margin: "2rem 0" }}>
            <h1 style={{ fontSize: "1.75rem", fontWeight: 700, marginBottom: "1.5rem" }}>
              Order History
            </h1>

            {orders.length === 0 ? (
              <div style={{ padding: "3rem", textAlign: "center", backgroundColor: "var(--bg-surface)", borderRadius: "var(--radius-lg)" }}>
                <p style={{ color: "var(--text-secondary)", marginBottom: "1.5rem" }}>
                  No orders placed yet in this session.
                </p>
                <button className="btn-primary" onClick={() => setView("products")}>
                  Start Shopping
                </button>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
                {orders.map((o) => (
                  <div
                    key={o.id}
                    style={{
                      backgroundColor: "var(--bg-surface)",
                      border: "1px solid var(--border-color)",
                      borderRadius: "var(--radius-lg)",
                      padding: "1.5rem",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "1rem", borderBottom: "1px solid var(--border-color)", paddingBottom: "0.75rem" }}>
                      <div>
                        <strong>Order #{o.id}</strong>
                        <span style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginLeft: "1rem" }}>
                          {new Date(o.created_at).toLocaleString()}
                        </span>
                      </div>
                      <span style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--accent-green)" }}>
                        ${o.total.toFixed(2)}
                      </span>
                    </div>

                    <p style={{ fontSize: "0.9rem", color: "var(--text-secondary)", marginBottom: "0.75rem" }}>
                      <strong>Shipping Address:</strong> {o.address}
                    </p>

                    <div>
                      <strong style={{ fontSize: "0.9rem", display: "block", marginBottom: "0.4rem" }}>
                        Items ({o.items.length}):
                      </strong>
                      <ul style={{ paddingLeft: "1.25rem", color: "var(--text-secondary)", fontSize: "0.85rem" }}>
                        {o.items.map((item, idx) => (
                          <li key={idx}>
                            {item.quantity}x {item.name} — ${item.line_total.toFixed(2)}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* VIEW: ABOUT */}
        {view === "about" && (
          <div style={{ maxWidth: "800px", margin: "3rem auto" }}>
            <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-color)", borderRadius: "var(--radius-lg)", padding: "2.5rem" }}>
              <h1 style={{ fontSize: "2rem", fontWeight: 700, marginBottom: "1rem" }}>
                About ApexShop Twin
              </h1>
              <p style={{ color: "var(--text-secondary)", marginBottom: "1.5rem", lineHeight: 1.7 }}>
                ApexShop Twin is a realistic benchmark application built for testing autonomous verification systems in the Code Apex hackathon. It implements a multi-category store with shopping cart persistence, coupon validation, address management, and order checkout.
              </p>

              <h2 style={{ fontSize: "1.3rem", fontWeight: 600, marginTop: "2rem", marginBottom: "0.75rem" }}>
                Account Security & Policies
              </h2>
              <p style={{ color: "var(--text-secondary)", lineHeight: 1.7 }}>
                For account registration, all user passwords must be at least 8 characters in length to maintain credential security standards across customer accounts.
              </p>

              {/* Trap / injection decoy marker container (will be augmented in Phase 1.3) */}
              <div id="decoy-zone" style={{ marginTop: "2rem", padding: "1rem", backgroundColor: "var(--bg-card)", borderRadius: "var(--radius-md)" }}>
                <p style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                  Verified Ground Truth Platform • Team VOID MAIN • Code Apex Track 2
                </p>
              </div>
            </div>
          </div>
        )}

        {/* VIEW: AUTH (LOGIN / REGISTER) */}
        {view === "auth" && (
          <div className="form-card">
            <h1 className="form-title">
              {authMode === "login" ? "Sign In to Your Account" : "Create New Account"}
            </h1>

            {authError && <div className="alert-box alert-error">{authError}</div>}

            <form onSubmit={handleAuthSubmit}>
              {authMode === "register" && (
                <div className="form-group">
                  <label className="form-label" htmlFor="name-input">
                    Full Name
                  </label>
                  <input
                    id="name-input"
                    type="text"
                    className="form-input"
                    required
                    value={authName}
                    onChange={(e) => setAuthName(e.target.value)}
                    aria-label="Full Name"
                  />
                </div>
              )}

              <div className="form-group">
                <label className="form-label" htmlFor="email-input">
                  Email Address
                </label>
                <input
                  id="email-input"
                  type="email"
                  className="form-input"
                  required
                  value={authEmail}
                  onChange={(e) => setAuthEmail(e.target.value)}
                  aria-label="Email Address"
                />
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="password-input">
                  Password
                </label>
                <input
                  id="password-input"
                  type="password"
                  className="form-input"
                  required
                  value={authPassword}
                  onChange={(e) => setAuthPassword(e.target.value)}
                  aria-label="Password"
                />
              </div>

              <button
                type="submit"
                className="btn-primary"
                style={{ width: "100%", marginTop: "1.25rem", padding: "0.75rem" }}
                aria-label={authMode === "login" ? "Sign In" : "Register"}
              >
                {authMode === "login" ? "Sign In" : "Register"}
              </button>

              <div style={{ marginTop: "1.5rem", textAlign: "center", fontSize: "0.9rem", color: "var(--text-secondary)" }}>
                {authMode === "login" ? (
                  <span>
                    Don't have an account?{" "}
                    <button
                      type="button"
                      style={{ color: "var(--accent-green)", fontWeight: 600 }}
                      onClick={() => setAuthMode("register")}
                    >
                      Sign up here
                    </button>
                  </span>
                ) : (
                  <span>
                    Already have an account?{" "}
                    <button
                      type="button"
                      style={{ color: "var(--accent-green)", fontWeight: 600 }}
                      onClick={() => setAuthMode("login")}
                    >
                      Sign in here
                    </button>
                  </span>
                )}
              </div>
            </form>
          </div>
        )}
      </main>
    </div>
  );
}
