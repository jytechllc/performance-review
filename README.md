This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.

## Tech Stack
| Layer                 | Technology                |
| --------------------- | ------------------------- |
| Frontend              | Next.js 15 (App Router)   |
| UI                    | Tailwind CSS + shadcn/ui  |
| Backend API           | Next.js Route Handlers    |
| ORM                   | Prisma                    |
| Database              | PostgreSQL                |
| Scheduler             | Vercel Cron               |
| Deployment            | Vercel                    |
| External Integrations | GitHub REST API           |

## Git Workflow & Branch Rules

### Branch Structure

```bash
main

feature/*
bugfix/*
```

---

## Main Branch Rules

### `main`
Production-ready branch.

#### Rules
- NEVER push directly to `main`
- Merge only through Pull Requests
- Must pass code review
- Must pass build/tests
- Always deployable

#### Purpose
Stable final version for presentation/demo.

---

## Feature Branch Naming

### Format

```bash
feature/<service>/<feature-name>
```

### Examples

```bash
feature/auth/login
feature/github/retrieval
```

---

## Bugfix Branch Naming

### Format

```bash
bugfix/<module>/<issue>
```

### Examples

```bash
bugfix/auth/login
bugfix/github/null-pointer
```

---

## Development Workflow
(Maybe wrong, I forgot the percedure)

### 1. Pull latest code

```bash
git checkout main
git pull origin main
```

---

### 2. Create a feature branch

```bash
git checkout -b feature/auth/login
```

---

### 3. Commit code

### Commit Message Rules

```bash
feat: implement JWT login
fix: resolve onboarding validation bug
test: add unit tests
```

#### Commit Types

| Type | Description |
|------|-------------|
| feat | New feature |
| fix | Bug fix |
| test | Testing |
| chore | Config/dependency updates |

---

### 4. Push branch

```bash
git push origin feature/auth/login
```

---

### 5. Create Pull Request

```text
feature/auth/login
        ↓
       main
```

### PR Requirements
- At least 1 reviewer
- No merge conflicts (solve conflicts before merging locally)
- Build passes
- Application runs successfully

---

## Forbidden Actions

### DO NOT

#### Push directly to `main`

#### Develop multiple features in one branch

Bad example:

```bash
feature/login-and-profile-and-s3
```

#### Keep branches too long without merging

Merge frequently to avoid conflicts.

#### Push code that cannot compile/run

All services should remain runnable.

