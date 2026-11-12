# Deploying the demo on AWS

The demo is a single static web page: `public/index.html` (a copy of `build/lactalis_demo.html`).
It needs no server, database or build step. All data inside it is synthetic.

## Option 1: AWS Amplify, upload a zip (easiest, about 5 minutes)

1. Open the AWS console and go to **AWS Amplify**.
2. Choose **Create new app**, then **Deploy without Git**.
3. Give the app a name (for example `demand-supply-control-tower`) and an environment name (for example `main`).
4. Upload **`lactalis-demo-website.zip`**. It contains only `index.html` at the top level.
5. Choose **Save and deploy**. Amplify gives a link like `https://main.xxxxxxxx.amplifyapp.com`.

## Option 2: AWS Amplify, connected to the GitHub repo

1. In Amplify choose **Create new app**, then **GitHub**, and pick the repository and the `main` branch.
2. Amplify reads `amplify.yml` from the repo: no build, and it publishes the `public` folder.
3. Choose **Save and deploy**. Every push to `main` redeploys automatically.

## Password protection on AWS

In Amplify: **Hosting > Access control > Manage access**, set the branch to **Restricted**, and choose a username and password.

- Visitors get a browser pop-up for the username and password before the page loads.
- Browsers remember this password until the browser is closed. To ask on every single visit (as the Vercel version does), put the site behind CloudFront with a Lambda@Edge function instead; ask the demo author for that version.

## Files that only matter on Vercel

`vercel.json`, `.vercelignore` and `middleware.js` are for Vercel and are ignored by AWS. They are safe to leave in place.

## The demo's own sign-in screen

After the AWS password, the demo shows its own admin sign-in screen. It is for the presentation only and is not security: the username and password are pre-filled, so just choose **Sign in**. Details are in `build/README.md`.

## Rebuilding the demo after a change

See `README.md`, section "Rebuild". The build script writes both `build/lactalis_demo.html` and `public/index.html`.
