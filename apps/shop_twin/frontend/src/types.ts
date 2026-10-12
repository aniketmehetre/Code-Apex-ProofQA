export interface Product {
  id: number;
  name: string;
  category: string;
  price: number;
  description: string;
  stock: number;
  rating: number;
  image_url: string;
}

export interface ProductsResponse {
  products: Product[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface CartLineItem {
  id: number;
  product_id: number;
  name: string;
  price: number;
  quantity: number;
  line_total: number;
  category: string;
}

export interface Cart {
  items: CartLineItem[];
  item_count: number;
  subtotal: number;
  discount: number;
  total: number;
  applied_coupon: string | null;
}

export interface Order {
  id: number;
  total: number;
  subtotal: number;
  discount: number;
  address: string;
  created_at: string;
  items: CartLineItem[];
}

export interface User {
  id: number;
  email: string;
  name: string;
}
