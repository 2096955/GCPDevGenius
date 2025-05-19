#!/usr/bin/env python3
import os
from PIL import Image, ImageDraw, ImageFont
import base64
import io

# Create directory if it doesn't exist
os.makedirs('images', exist_ok=True)

# Create a blank image with white background
img_width, img_height = 400, 300
image = Image.new('RGB', (img_width, img_height), color='white')
draw = ImageDraw.Draw(image)

# Add a blue rectangle for the GCP style
draw.rectangle([(50, 50), (350, 250)], fill='#4285F4')

# Add text
text = "DevGenius App"
text_color = 'white'
try:
    # Try to use a system font - this might not work on all systems
    font = ImageFont.truetype("Arial", 36)
except IOError:
    # Fall back to default font
    font = ImageFont.load_default()

# Calculate text position to center it
text_width = draw.textlength(text, font=font)
text_position = ((img_width - text_width) / 2, img_height / 2 - 18)

# Draw text on image
draw.text(text_position, text, fill=text_color, font=font)

# Save the image
image.save('images/Devgenius_app.png')

# Also generate the image as a base64 string for inline usage
buffer = io.BytesIO()
image.save(buffer, format='PNG')
img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')

print(f"Image saved to images/Devgenius_app.png")
print("\nBase64 encoded image string for inline usage:")
print(img_str) 