export interface FindingItem {
  id: string;
  oracle_class: string;
  tier: 'VERIFIED' | 'VERIFIED_VIOLATION' | 'INTERMITTENT' | 'SUSPECTED' | 'INSUFFICIENT_EVIDENCE';
  claim: string;
  signature: {
    kind: string;
    first_party_endpoint: string;
    status: number;
    error_type?: string;
    message_norm: string;
  };
  steps: Array<{
    id: string;
    kind: string;
    locator?: { role?: string; name?: string; testid?: string };
    value?: string;
  }>;
  confidence: number;
}

export const MOCK_FINDINGS: FindingItem[] = [
  {
    id: "f_b01_zero_qty",
    oracle_class: "A",
    tier: "VERIFIED",
    claim: "Zero quantity cart addition returns HTTP 500 ZeroQuantityException",
    signature: {
      kind: "http_5xx",
      first_party_endpoint: "/api/cart",
      status: 500,
      error_type: "ZeroQuantityException",
      message_norm: "ZeroQuantityException on /api/cart"
    },
    steps: [
      { id: "s0", kind: "goto", value: "/" },
      { id: "s1", kind: "click", locator: { role: "heading", name: "Noise-Canceling Headphones" } },
      { id: "s2", kind: "fill", locator: { role: "spinbutton", name: "Quantity" }, value: "0" },
      { id: "s3", kind: "click", locator: { role: "button", name: "Confirm Add to Cart", testid: "modal-add-to-cart" } }
    ],
    confidence: 1.0
  },
  {
    id: "f_b03_badge_divergence",
    oracle_class: "D",
    tier: "VERIFIED_VIOLATION",
    claim: "Cart badge displays count + 1 after item deletion (UI vs Network state inconsistency)",
    signature: {
      kind: "cross_layer_inconsistency",
      first_party_endpoint: "/api/cart",
      status: 200,
      message_norm: "Badge count 2 does not match backend cart items 1"
    },
    steps: [
      { id: "s0", kind: "goto", value: "/" },
      { id: "s1", kind: "click", locator: { role: "button", name: "Add to Cart" } },
      { id: "s2", kind: "click", locator: { role: "button", name: "Cart (1)" } },
      { id: "s3", kind: "click", locator: { role: "button", name: "Remove Item" } }
    ],
    confidence: 0.98
  },
  {
    id: "f_b10_sql_injection",
    oracle_class: "A",
    tier: "VERIFIED",
    claim: "Product search quotes trigger 500 Internal Server Error (SQL Syntax Exception)",
    signature: {
      kind: "http_5xx",
      first_party_endpoint: "/api/products",
      status: 500,
      error_type: "OperationalError",
      message_norm: "OperationalError: unrecognized token near syntax"
    },
    steps: [
      { id: "s0", kind: "goto", value: "/" },
      { id: "s1", kind: "fill", locator: { role: "searchbox", name: "Search" }, value: "'" }
    ],
    confidence: 1.0
  }
];

export const MOCK_GRAPH_NODES = [
  { id: "node_home", label: "Catalog (/)", visits: 24, hasBug: false, x: 100, y: 150 },
  { id: "node_detail", label: "Product Modal", visits: 18, hasBug: false, x: 280, y: 80 },
  { id: "node_cart", label: "Shopping Cart (/cart)", visits: 14, hasBug: true, x: 280, y: 220 },
  { id: "node_checkout", label: "Checkout (/checkout)", visits: 8, hasBug: false, x: 460, y: 220 },
  { id: "node_orders", label: "Orders History", visits: 6, hasBug: false, x: 620, y: 150 },
  { id: "node_about", label: "About (/about)", visits: 4, hasBug: false, x: 460, y: 80 }
];

export const MOCK_GRAPH_EDGES = [
  { from: "node_home", to: "node_detail", label: "open_product" },
  { from: "node_detail", to: "node_cart", label: "add_to_cart [B01 Trigger]" },
  { from: "node_home", to: "node_cart", label: "view_cart" },
  { from: "node_cart", to: "node_checkout", label: "proceed_checkout" },
  { from: "node_checkout", to: "node_orders", label: "complete_order" },
  { from: "node_home", to: "node_about", label: "security_info" }
];

export const MOCK_BENCH_SUMMARY = {
  true_bugs_count: 1,
  total_ground_truth: 10,
  precision: 1.0,
  precision_ci: [0.2065, 1.0],
  recall: 0.1,
  recall_ci: [0.0179, 0.4042],
  certificate_validity_rate: 1.0,
  certificate_validity_ci: [0.5655, 1.0],
  decoy_false_positive_rate: 0.0,
  average_shrink_reduction_pct: 70.0,
  total_certificates_evaluated: 5,
  adversarial_hijack_rate: 0.0,
  adversarial_hijacks_count: 0
};
