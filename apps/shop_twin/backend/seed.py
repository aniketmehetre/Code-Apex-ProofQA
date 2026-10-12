"""Deterministic database seeder for the shop twin benchmark target."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sqlmodel import Session, SQLModel, create_engine  # noqa: E402

from apps.shop_twin.backend.models import Coupon, Product, User  # noqa: E402

DEFAULT_SEED_DB_PATH = Path(__file__).resolve().parent / "seed.db"


def seed_database(db_path: Path = DEFAULT_SEED_DB_PATH) -> None:
    """Create a pristine deterministic SQLite database with 60 products, 4 categories, 3 coupons."""
    if db_path.exists():
        db_path.unlink()

    engine = create_engine(f"sqlite:///{db_path}")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        # 1. Seed 4 Categories with 15 products each (60 products total)
        categories = ["Electronics", "Clothing", "Books", "Home"]
        products_data = [
            # Electronics (15)
            ("Noise-Canceling Wireless Headphones", "Electronics", 149.99, "Over-ear bluetooth headphones with active ANC", 4.8),
            ("Ultra-Slim Ergonomic Mechanical Keyboard", "Electronics", 89.50, "Hot-swappable tactile switches with RGB", 4.7),
            ("High-Precision Optical Gaming Mouse", "Electronics", 49.99, "16000 DPI sensor with programmable buttons", 4.6),
            ("4K Ultra-HD 27-inch IPS Monitor", "Electronics", 299.99, "Color-accurate creator monitor with USB-C", 4.9),
            ("Portable USB-C Fast Charger 65W", "Electronics", 29.99, "GaN technology ultra-compact dual port charger", 4.5),
            ("Aluminum Multi-Angle Laptop Stand", "Electronics", 35.00, "Foldable ergonomic riser for desks", 4.6),
            ("1080p Full-HD Autofocus Webcam", "Electronics", 59.90, "Built-in stereo microphone and privacy cover", 4.4),
            ("Waterproof Bluetooth Speaker", "Electronics", 45.00, "Deep bass and 12-hour continuous battery", 4.5),
            ("Smart Watch Activity Tracker", "Electronics", 119.00, "Heart rate, SpO2, and GPS tracking watch", 4.3),
            ("True Wireless Earbuds with Case", "Electronics", 69.99, "IPX7 sweatproof with wireless charging case", 4.5),
            ("Braided USB-C Cable 2-Pack", "Electronics", 14.99, "Durable nylon braided high-speed sync cable", 4.4),
            ("RGB Large Gaming Desk Mat", "Electronics", 24.50, "Micro-textured cloth surface with anti-slip base", 4.6),
            ("Compact Portable Power Bank 20000mAh", "Electronics", 39.99, "Triple output with PD fast charging support", 4.7),
            ("Smart Home Voice Assistant Speaker", "Electronics", 79.99, "Far-field microphones and smart hub built-in", 4.2),
            ("High-Speed Wireless Router Wi-Fi 6", "Electronics", 129.99, "Gigabit speeds with multi-device beamforming", 4.6),

            # Clothing (15)
            ("Classic Heavyweight Crewneck T-Shirt", "Clothing", 24.99, "100% organic combed cotton everyday shirt", 4.5),
            ("Slim-Fit Raw Denim Jeans", "Clothing", 69.99, "Durable stretch indigo denim with tailored cut", 4.4),
            ("Fleece Zip-Up Hoodie", "Clothing", 49.90, "Brushed fleece interior with metal zipper", 4.7),
            ("Merino Wool Crewneck Sweater", "Clothing", 89.00, "Thermal breathable ultra-fine natural wool", 4.8),
            ("Water-Resistant All-Weather Windbreaker", "Clothing", 75.00, "Packable lightweight jacket with storm hood", 4.6),
            ("Performance Moisture-Wicking Joggers", "Clothing", 39.99, "Athletic tapered pants with zipper pockets", 4.5),
            ("Casual Button-Down Linen Shirt", "Clothing", 45.00, "Relaxed breathable summer casual shirt", 4.3),
            ("Padded Puffer Winter Jacket", "Clothing", 120.00, "Recycled insulation with fleece lined pockets", 4.7),
            ("Cushioned Athletic Ankle Socks 6-Pack", "Clothing", 16.50, "Arch support and seamless toe comfort", 4.8),
            ("Canvas Classic Low-Top Sneakers", "Clothing", 55.00, "Vulcanized rubber sole with timeless silhouette", 4.4),
            ("Structured Cotton Baseball Cap", "Clothing", 19.99, "Adjustable strapback with pre-curved visor", 4.2),
            ("Thermal Base Layer Top", "Clothing", 29.99, "Moisture management for cold weather outdoor sports", 4.6),
            ("Relaxed Fit Khaki Chinos", "Clothing", 52.00, "Wrinkle-resistant everyday stretch trousers", 4.5),
            ("Leather Minimalist Reversible Belt", "Clothing", 32.00, "Full-grain leather with brushed metal buckle", 4.4),
            ("Polarized UV400 Sunglasses", "Clothing", 38.50, "Lightweight acetate frame with anti-glare lenses", 4.5),

            # Books (15)
            ("Designing Data-Intensive Applications", "Books", 48.00, "The big ideas behind reliable, scalable systems", 5.0),
            ("Structure and Interpretation of Computer Programs", "Books", 55.00, "Classic computer science principles and Lisp", 4.9),
            ("Clean Code: A Handbook of Agile Software", "Books", 42.50, "Principles, patterns, and craftsmanship guide", 4.6),
            ("Introduction to Algorithms (CLRS)", "Books", 85.00, "Comprehensive algorithms and data structures reference", 4.8),
            ("The Pragmatic Programmer: 20th Anniversary", "Books", 44.00, "Your journey to software mastery", 4.9),
            ("Refactoring: Improving Existing Code", "Books", 47.50, "Catalog of refactorings and code smells", 4.7),
            ("Database Internals: Distributed Storage", "Books", 52.00, "Deep dive into storage engines and Raft consensus", 4.8),
            ("Site Reliability Engineering: How Google Runs", "Books", 39.99, "Production engineering and systems management", 4.7),
            ("Understanding Distributed Systems", "Books", 34.00, "Communication, coordination, and fault tolerance", 4.8),
            ("Domain-Driven Design: Tackling Complexity", "Books", 56.00, "Strategic software patterns for core domain logic", 4.6),
            ("High Performance Browser Networking", "Books", 38.00, "TCP, UDP, HTTP/2, and browser optimizations", 4.7),
            ("Operating Systems: Three Easy Pieces", "Books", 28.00, "Virtualization, concurrency, and persistence fundamentals", 4.9),
            ("Computer Systems: A Programmer Perspective", "Books", 79.00, "Architecture, compilers, memory hierarchy", 4.8),
            ("Rust in Action: Systems Programming", "Books", 46.00, "Memory safety and low-level programming in Rust", 4.7),
            ("Types and Programming Languages", "Books", 65.00, "Foundational type systems and operational semantics", 4.8),

            # Home (15)
            ("Ergonomic Mesh Task Office Chair", "Home", 189.99, "Breathable back with adjustable lumbar support", 4.7),
            ("Dimmable LED Desk Lamp with Wireless Charger", "Home", 39.99, "Color temperature touch controls and USB port", 4.5),
            ("Stainless Steel Thermal French Press", "Home", 32.50, "Double-wall insulated coffee maker 34oz", 4.8),
            ("Ceramic Stoneware Mug Set of 4", "Home", 26.00, "Handmade glaze microwave and dishwasher safe", 4.6),
            ("Ultra-Soft Microfiber Bed Sheet Set", "Home", 35.00, "Deep pocket breathable cooling bed linen", 4.5),
            ("Aroma Essential Oil Ultrasonic Diffuser", "Home", 28.99, "Quiet ambient lighting and auto shut-off", 4.4),
            ("Non-Stick Cast Iron Skillet 10-inch", "Home", 29.50, "Pre-seasoned heavy duty pan with heat silicone grip", 4.8),
            ("Bamboo Multi-Tier Spice Rack Organizer", "Home", 22.00, "Expandable tiered kitchen counter shelf", 4.5),
            ("Heavyweight Blackout Window Curtains", "Home", 42.00, "Thermal noise reduction grommet panels", 4.6),
            ("Large Storage Baskets Fabric Set of 3", "Home", 25.00, "Collapsible closet organization bins with handles", 4.4),
            ("Stainless Steel Kitchen Knife Set with Block", "Home", 89.99, "High carbon precision cutting culinary set", 4.7),
            ("Weighted Sensory Blanket 15 lbs", "Home", 58.00, "Even pressure distribution with soft cotton cover", 4.6),
            ("Electric Gooseneck Temperature Kettle", "Home", 64.00, "Precision pour spout with 1-degree temperature dial", 4.9),
            ("Robot Vacuum Cleaner with Smart Mapping", "Home", 219.00, "App control with auto-boost carpet suction", 4.5),
            ("Handcrafted Scented Soy Wax Candle", "Home", 18.00, "Cedarwood and amber slow-burning aromatics", 4.7),
        ]

        assert len(products_data) == 60, f"Expected 60 products, got {len(products_data)}"
        assert set(cat for _, cat, _, _, _ in products_data) == set(categories)

        for name, category, price, desc, rating in products_data:
            session.add(
                Product(
                    name=name,
                    category=category,
                    price=price,
                    description=desc,
                    rating=rating,
                    stock=100,
                    image_url=f"/images/{category.lower()}.png",
                )
            )

        # 2. Seed 3 Coupons
        coupons = [
            Coupon(code="SAVE10", discount_percent=10.0, active=True),
            Coupon(code="APEX20", discount_percent=20.0, active=True),
            Coupon(code="HALF50", discount_percent=50.0, active=True),
        ]
        for c in coupons:
            session.add(c)

        # 3. Seed Default Test User (test@example.com / password123)
        default_user = User(
            email="test@example.com",
            password_hash="sha256:ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f",  # sha256(password123)
            name="Test User",
            address="123 Benchmark Ave, Suite 100",
        )
        session.add(default_user)

        session.commit()

    print(f"Pristine seed database created at {db_path} with 60 products, 4 categories, 3 coupons.")


if __name__ == "__main__":
    seed_database()
