# Core Concepts

## resource

A **resource** is a named ML artifact registered in the monorepo (e.g. `fraud-detector`, `embedder`). It has a description and one or more versioned entries.

resources are registered once and can accumulate versions over time. Removing a resource is blocked if any group still references it.

---

## resource Version

A **resource version** is a specific, immutable snapshot of a resource (e.g. `fraud-detector@2.1.0`). It holds:

- A **path** to the artifact (relative to the monorepo root)
- An optional **pull command** and **push command** that override the global config
- Metadata: `created_at`, `created_by`

Versions must be valid [semver](https://semver.org/) strings. Removing a version is blocked if any group version pins it.

---

## resource Group

A **group** is a named, versioned snapshot that pins specific versions of multiple resources (e.g. `production@1.4.0` → `fraud-detector@2.1.0` + `embedder@0.9.4`).

Groups act like a lock file: they give a single version string that represents a known-good combination of resource versions. When you release a new group version, its semver must be greater than the previous latest.

---

## App

An **app** is any package in the monorepo that declares a dependency on a group version via a local `.resver/app.yml` file. It does not need to know individual resource versions — it only tracks the group version.

```
monorepo/
├── .resver/
│   ├── registry.yml          ← source of truth
│   └── config.yml            ← global pull/push backend
├── apps/
│   ├── fraud-service/
│   │   └── .resver/
│   │       └── app.yml       ← group: production, version: "1.4.0"
│   └── recommender/
│       └── .resver/
│           └── app.yml       ← group: staging, version: "0.2.0"
```

---

## Relationship Diagram

```
resource ──has many──► resource Version
                         │
                    pinned by
                         │
Group ──has many──► Group Version
                         │
                    declared by
                         │
                        App
```
