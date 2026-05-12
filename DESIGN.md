---
name: Abasto Heritage Modern
colors:
  surface: '#fcf9f8'
  surface-dim: '#dcd9d9'
  surface-bright: '#fcf9f8'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f6f3f2'
  surface-container: '#f0eded'
  surface-container-high: '#eae7e7'
  surface-container-highest: '#e4e2e1'
  on-surface: '#1b1c1c'
  on-surface-variant: '#404941'
  inverse-surface: '#303030'
  inverse-on-surface: '#f3f0f0'
  outline: '#717970'
  outline-variant: '#c0c9be'
  surface-tint: '#306a43'
  primary: '#002c13'
  on-primary: '#ffffff'
  primary-container: '#014421'
  on-primary-container: '#76b284'
  inverse-primary: '#97d5a5'
  secondary: '#735c00'
  on-secondary: '#ffffff'
  secondary-container: '#fed65b'
  on-secondary-container: '#745c00'
  tertiary: '#232525'
  on-tertiary: '#ffffff'
  tertiary-container: '#383b3b'
  on-tertiary-container: '#a3a5a4'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#b2f1bf'
  primary-fixed-dim: '#97d5a5'
  on-primary-fixed: '#00210d'
  on-primary-fixed-variant: '#14512d'
  secondary-fixed: '#ffe088'
  secondary-fixed-dim: '#e9c349'
  on-secondary-fixed: '#241a00'
  on-secondary-fixed-variant: '#574500'
  tertiary-fixed: '#e1e3e2'
  tertiary-fixed-dim: '#c5c7c6'
  on-tertiary-fixed: '#191c1c'
  on-tertiary-fixed-variant: '#454747'
  background: '#fcf9f8'
  on-background: '#1b1c1c'
  surface-variant: '#e4e2e1'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '600'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '500'
    lineHeight: '1.3'
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: '1.0'
    letterSpacing: 0.05em
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: '1.0'
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 8px
  container-max: 1280px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 40px
  section-gap: 80px
---

## Brand & Style

This design system establishes a "Digital Atelier" aesthetic for the modern grocer. It merges the prestige of a high-end boutique with the efficiency of a smart logistics platform. The brand personality is grounded, sophisticated, and transparent, aimed at affluent urban professionals who value ingredient provenance and frictionless shopping.

The visual style is **Premium Minimalism**. It avoids the clutter typical of mass-market retail, instead utilizing generous negative space and a refined color story to let product photography (the "freshness") serve as the primary visual driver. The interface feels "smart" through subtle motion, precise typography, and a structural layout that implies organization and quality.

## Colors

The palette is anchored by **Deep Forest Green**, used for primary actions and brand architecture to evoke growth and organic stability. **Subtle Gold** is reserved for high-value micro-interactions, loyalty indicators, and premium "Selection" tags, acting as a sophisticated "chef’s kiss" rather than a dominant hue.

The background is a **Crisp White**, though structural surfaces use a very faint grey-green wash (#F8F9F8) to maintain softness and prevent eye strain. Text is rendered in a deep charcoal (#2D2D2D) rather than pure black to preserve the premium, organic feel of the brand.

## Typography

This design system utilizes **Inter** for its exceptional legibility and systematic precision. The type hierarchy is intentionally spacious, prioritizing breathing room over information density. 

Headlines use tighter letter-spacing and heavier weights to project authority, while body copy maintains a generous 1.6 line-height to evoke the feeling of an editorial culinary magazine. Labels and metadata use uppercase styling with increased tracking to differentiate "utilitarian" data from "inspirational" content.

## Layout & Spacing

The layout follows a **Fixed Grid** model for desktop to ensure product photography maintains its intended aspect ratio and impact. We use a 12-column system with wide 24px gutters.

The "Freshness" rhythm is achieved through verticality; sections are separated by significant 80px gaps, preventing the "digital flyer" look and instead feeling like a curated gallery. For mobile, a 4-column grid is used with a 16px safe area. Padding within components (like cards) should be generous—never less than 24px—to maintain the minimalist philosophy.

## Elevation & Depth

This design system avoids heavy shadows, instead using **Tonal Layers** and **Low-Contrast Outlines**. 

Depth is primarily created through subtle color shifts (e.g., a white card on a #F8F9F8 background). When elevation is required for interactivity (like a hovering product card), use a single, ultra-diffused "Ambient Shadow": 0px 12px 32px rgba(1, 68, 33, 0.04). This adds a faint green tint to the shadow, making the interface feel cohesive and organic rather than sterile.

## Shapes

The shape language is **Rounded**, signifying friendliness and the soft forms found in nature (produce, grains, leaves). 

Standard UI elements like input fields and buttons utilize a 0.5rem (8px) radius. Larger containers, such as product cards and promotional banners, use the `rounded-lg` (16px) or `rounded-xl` (24px) tokens to create a softer, more approachable frame for imagery. Interaction states should never feel sharp or aggressive.

## Components

### Buttons
Primary buttons are solid Deep Forest Green with white text, using the 0.5rem radius. Secondary buttons use a 1px border of the primary color with a transparent background. The "Add to Cart" action should be a tactile, high-affordance button with a gold micro-interaction on success.

### Cards
Product cards are the core component. They feature a clean white surface, no border, and the "Ambient Shadow" on hover. Imagery must be high-resolution on a neutral or natural background. Prices are displayed in the primary green, while "Premium" badges are rendered in gold with Inter Medium.

### Input Fields
Inputs are minimalist: a bottom-border only or a very light grey-green stroke. Focus states transition the border to Deep Forest Green. Typography within inputs should be clean and spacious.

### Chips & Filters
Used for dietary tags (Organic, Vegan, Gluten-Free). These are pill-shaped with a light green tint (#E6ECE9) and primary green text. They should feel light and easy to dismiss.

### Smart Integration Features
- **The "Provenence" Tab:** A specialized list component with gold icons indicating the farm-to-table journey of a product.
- **Smart Cart:** A slide-out panel using backdrop blurs (glassmorphism) to overlay the shopping experience, keeping the user in the context of the "Fresh Market."
- **Recipe-to-Cart:** A unique component that allows users to add all ingredients from a recipe card with a single gold-accented button.