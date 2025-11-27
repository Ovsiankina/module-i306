"""Seed data used to hydrate the dev database when it is empty."""

DEFAULT_ITEMS = [
	{
		"name": "iPhone 12",
		"price": 799.0,
		"category": "Apple",
		"image": "https://www.gizmochina.com/wp-content/uploads/2020/05/iphone-12-pro-max-family-hero-all-600x600.jpg",
		"details": "6.1-inch OLED display<br>A14 Bionic chip<br>256GB storage",
		"price_id": "price_1Jk8KjBZlBPWG6ECQXNqcKhR",
		"inventory": {"stock_quantity": 5, "low_stock_threshold": 1, "is_published": True},
	},
	{
		"name": "iPhone 12 mini",
		"price": 729.0,
		"category": "Apple",
		"image": "https://fdn2.gsmarena.com/vv/pics/apple/apple-iphone-12-mini-2.jpg",
		"details": "5.4-inch Super Retina XDR display<br>Dual 12MP camera system<br>256 GB storage",
		"price_id": "price_1Jk8LrBZlBPWG6ECvsEjYsZF",
		"inventory": {"stock_quantity": 8, "low_stock_threshold": 2, "is_published": True},
	},
	{
		"name": "iPhone 11",
		"price": 699.0,
		"category": "Apple",
		"image": "https://www.gizmochina.com/wp-content/uploads/2019/09/Apple-iPhone-11-1.jpg",
		"details": "A13 Bionic chip<br>smart HDR<br>128GB storage",
		"price_id": "price_1Jk8MUBZlBPWG6ECueOfWc9N",
		"inventory": {"stock_quantity": 6, "low_stock_threshold": 1, "is_published": True},
	},
	{
		"name": "Acer Nitro 5",
		"price": 1300.0,
		"category": "Laptop",
		"image": "/static/uploads/nitro.jpg",
		"details": "Intel i7 10th gen<br>1920*1080 144Hz display<br>8 GB RAM<br>1 TB HDD + 256 GB SSD<br>GTX 1650 Graphics card",
		"price_id": "price_1JlBEmBZlBPWG6EC1i6RYpTB",
		"inventory": {"stock_quantity": 3, "low_stock_threshold": 1, "is_published": True},
	},
	{
		"name": "Apple MacBook Pro",
		"price": 1990.0,
		"category": "Laptop",
		"image": "/static/uploads/macbook.jpg",
		"details": "Intel core i5 2.4GHz<br>13.3\" Retina Display<br>8 GB RAM<br>256 GB SSD<br>Touch Bar + Touch id",
		"price_id": "price_1JlBIQBZlBPWG6ECsPx49z0g",
		"inventory": {"stock_quantity": 4, "low_stock_threshold": 1, "is_published": True},
	},
	{
		"name": "Mi TV 4X",
		"price": 500.0,
		"category": "Television",
		"image": "/static/uploads/mi%20tv.jpg",
		"details": "108Cm 43\" UHD 4K LED<br>Smart Android TV<br>20W speakers Dolby™+ DTS-HD®",
		"price_id": "price_1JlBNABZlBPWG6ECzU6Yh1dq",
		"inventory": {"stock_quantity": 7, "low_stock_threshold": 2, "is_published": True},
	},
]

