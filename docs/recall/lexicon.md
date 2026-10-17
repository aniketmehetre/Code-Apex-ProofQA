# ProofQA 2.0: Control and Intent Lexicon

Documented lexicon for matching inverse pairs, metamorphic operations, and commerce/CRUD intents across arbitrary web controls.

## 1. Inverse Pairs
Used by `InversePairProbe` to systematically test add-then-remove, apply-then-clear, and check-then-uncheck transitions.

| Primary Action (Forward) | Matching Inverses (Backward) | Scope / Proximity Rule |
| :--- | :--- | :--- |
| `add`, `add to cart`, `add item`, `buy` | `remove`, `delete`, `trash`, `clear`, `decrement` | Matched within the same container / cart row or global cart |
| `apply`, `apply code`, `apply promo`, `redeem` | `remove`, `remove code`, `clear`, `cancel` | Matched within the coupon/promo container |
| `check`, `select`, `toggle on` | `uncheck`, `deselect`, `toggle off` | Same checkbox or toggle control |
| `increase`, `increment`, `plus` | `decrease`, `decrement`, `minus` | Sibling stepper buttons |

## 2. Independent Controls (State-Only Controls)
Used by `PairwiseProbe` on controls that do not change the URL path:
- **Pagination**: Next / Previous, Page numbers (`role=button`, `role=link`).
- **Filter**: Category filter, brand filter, price filter (`role=combobox`, `role=checkbox`, `role=radio`).
- **Sort**: Sort dropdown (`role=combobox`, labels containing `sort`, `order`, `price`, `rating`).
- **Search**: Search inputs and search buttons.

## 3. High-Level Intent Vocabulary (Generic Commerce / CRUD)
Shared between metamorphic probes, journey proposer (Prompt 7), and LLM journey proposer (Prompt 11):

| Intent | Match Keywords (Role, Label, Name, TestID) |
| :--- | :--- |
| `add_item` | `add to cart`, `add item`, `buy now`, `modal-add-to-cart` |
| `remove_item` | `remove`, `delete`, `trash`, `remove-item` |
| `apply_code` | `apply`, `apply coupon`, `redeem`, `promo` |
| `clear_code` | `clear`, `remove coupon`, `cancel` |
| `checkout` | `checkout`, `proceed to checkout`, `place order` |
| `register` | `register`, `sign up`, `create account` |
| `login` | `sign in`, `login`, `log in` |
| `update_profile` | `save`, `update profile`, `save changes`, `save address` |
| `search` | `search`, `find` |
| `sort` | `sort`, `order by`, `sort by` |
| `filter` | `filter`, `category`, `all categories` |
| `paginate` | `next`, `previous`, `page` |
