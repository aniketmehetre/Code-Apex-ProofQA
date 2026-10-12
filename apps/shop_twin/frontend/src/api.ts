import { Cart, Order, Product, ProductsResponse, User } from "./types";

const API_BASE = "/api";

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    credentials: "include",
  });

  if (!res.ok) {
    let errorDetail = "API request failed";
    try {
      const errJson = await res.json();
      errorDetail = errJson.detail || errJson.message || errorDetail;
    } catch {
      errorDetail = `HTTP ${res.status}: ${res.statusText}`;
    }
    throw new Error(errorDetail);
  }

  return res.json();
}

export const api = {
  getProducts: (params: { q?: string; category?: string; sort?: string; page?: number; page_size?: number }) => {
    const qp = new URLSearchParams();
    if (params.q) qp.set("q", params.q);
    if (params.category) qp.set("category", params.category);
    if (params.sort) qp.set("sort", params.sort);
    if (params.page) qp.set("page", params.page.toString());
    if (params.page_size) qp.set("page_size", params.page_size.toString());
    const qs = qp.toString();
    return request<ProductsResponse>(`/products${qs ? `?${qs}` : ""}`);
  },

  getCart: () => request<Cart>("/cart"),
  addToCart: (productId: number, quantity: number = 1) =>
    request<Cart>("/cart", {
      method: "POST",
      body: JSON.stringify({ product_id: productId, quantity }),
    }),
  updateCartItem: (itemId: number, quantity: number) =>
    request<Cart>(`/cart/${itemId}`, {
      method: "PATCH",
      body: JSON.stringify({ quantity }),
    }),
  removeCartItem: (itemId: number) =>
    request<Cart>(`/cart/${itemId}`, {
      method: "DELETE",
    }),
  applyCoupon: (code: string) =>
    request<{ status: string; coupon: string; discount_percent: number }>("/coupons/apply", {
      method: "POST",
      body: JSON.stringify({ code }),
    }),
  checkout: (address: string) =>
    request<{ status: string; order: Order }>("/checkout", {
      method: "POST",
      body: JSON.stringify({ address }),
    }),

  register: (email: string, password: string, name: string) =>
    request<{ status: string; user: User }>("/register", {
      method: "POST",
      body: JSON.stringify({ email, password, name }),
    }),
  login: (email: string, password: string) =>
    request<{ status: string; user: User }>("/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  logout: () => request<{ status: string }>("/logout", { method: "POST" }),
  getAddress: () => request<{ address: string | null }>("/account/address"),
  updateAddress: (address: string) =>
    request<{ status: string; address: string }>("/account/address", {
      method: "PUT",
      body: JSON.stringify({ address }),
    }),
  getOrders: () => request<Order[]>("/orders"),
};
