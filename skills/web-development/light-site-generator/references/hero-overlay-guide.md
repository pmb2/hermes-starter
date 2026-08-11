# Hero Overlay Guide

## the operator's Preference (Jul 29)

The hero image has a **subtle 10% dark overlay** (`rgba(0,0,0,0.1)`) via CSS `::after` pseudo-element.

**Evolution of this decision:**
1. Original had a heavy gradient overlay (`rgba(26,48,80,0.92)` → `rgba(26,48,80,0.6)`)
2. the operator said remove it entirely — image at full brightness (`..after { display: none }`)
3. Hero text became hard to read on lighter parts of the photo, even with text-shadow
4. the operator said "add a little bit back, maybe 10%" → settled on `rgba(0,0,0,0.1)`

## Implementation

### Light-Site Variant (assets/templates/light-site/index.html)

```css
.hero-bg { position: absolute; inset: 0; }
.hero-bg::after {
  content: '';
  position: absolute;
  inset: 0;
  background: rgba(0,0,0,0.1);  /* 10% — subtle, no more */
}
```

The overlay sits ON TOP of the hero image but BELOW the text content (`.hero .content` has `z-index: 1`).

### Duda-Clone Variant (assets/templates/duda-clone/template.html)

The Duda-clone template uses a different technique — **no gradient background**, the photo is the full visible background:

```css
.hero{color:#fff;padding:100px 0 80px;position:relative;overflow:hidden}
.hero::before{content:'';position:absolute;top:0;left:0;right:0;bottom:0;
  background:url('image') center/cover no-repeat;background-size:cover;z-index:0}
.hero::after{content:'';position:absolute;top:0;left:0;right:0;bottom:0;
  background:rgba(0,0,0,.1);z-index:1}
.hero .container{position:relative;z-index:2;text-align:center}
```

**Key difference:** `::before` = the photograph at full opacity (visible). `::after` = the 10% dark overlay. Container is `z-index: 2` above both pseudo-elements. No gradient background on `.hero` itself.

This is the preferred approach for premium-looking sites — the photo is fully visible, not fighting a gradient.

## Why 10% Works

- The hero image itself has warm tones (golden hour, truck, green lawn)
- 10% is barely perceptible as a darkening — the photo still looks vibrant
- White text on the darkened image passes WCAG contrast at most points
- Text-shadow (`0 2px 12px rgba(0,0,0,0.4)`) adds additional insurance for lighter regions of the image
- The user should NOT notice the overlay — it's a subtlety, not a design feature

## Dark Mode

In dark mode the hero image drops to 0.8 opacity. The `::after` overlay remains unchanged. The combined effect darkens the image further, which is appropriate for dark backgrounds.
