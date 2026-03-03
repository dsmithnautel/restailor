# Fix Remix Routing Context Error

## Problem

The application is throwing an invariant error when trying to use `<Link>` components:
```
invariant error at useHref
```

This occurs because Remix's `<Link>` component is being used outside of a proper router context.

## Root Cause

Looking at the code structure:
- [`root.tsx`](file:///Users/xalandames/Documents/Jake's%20Resume%20Converter/makeitjakes/frontend/app/root.tsx) renders `<Outlet />` which should provide the router context
- [`_index.tsx`](file:///Users/xalandames/Documents/Jake's%20Resume%20Converter/makeitjakes/frontend/app/routes/_index.tsx) contains `<Header />` and `<Footer />` which use `<Link>`
- [`header.tsx`](file:///Users/xalandames/Documents/Jake's%20Resume%20Converter/makeitjakes/frontend/app/components/header.tsx) has a `<Link to="/" />` 
- [`footer.tsx`](file:///Users/xalandames/Documents/Jake's%20Resume%20Converter/makeitjakes/frontend/app/components/footer.tsx) has a `<Link to="/privacy" />`

The issue is likely a Vite/Remix configuration problem or a hydration mismatch. Let me check the entry files and Vite config.

## Proposed Changes

### Investigation Phase
1. Check [`vite.config.ts`](file:///Users/xalandames/Documents/Jake's%20Resume%20Converter/makeitjakes/frontend/vite.config.ts) for potential misconfigurations
2. Check [`entry.client.tsx`](file:///Users/xalandames/Documents/Jake's%20Resume%20Converter/makeitjakes/frontend/app/entry.client.tsx) and [`entry.server.tsx`](file:///Users/xalandames/Documents/Jake's%20Resume%20Converter/makeitjakes/frontend/app/entry.server.tsx) for hydration issues

### Likely Fixes

#### Option 1: Fix Hydration Issue
If there's a hydration mismatch, ensure server and client rendering are aligned.

#### Option 2: Vite Configuration
Update Vite config to properly handle Remix SSR.

#### Option 3: Add Router Error Boundary
Add error boundary to gracefully handle routing errors.

## Verification Plan

### Manual Testing
1. Start the dev server: `npm run dev` (in `/Users/xalandames/Documents/Jake's Resume Converter/makeitjakes/frontend`)
2. Open browser to http://localhost:5173/
3. Verify the page loads without errors
4. Click the "Make it Jake's" logo link to ensure navigation works
5. Scroll to footer and click "Privacy Policy" link to test navigation to `/privacy`
6. Navigate back to home using browser back button

### Browser Console Check
Verify no React/Remix errors appear in the browser console.
