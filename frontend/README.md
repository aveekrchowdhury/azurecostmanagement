# Azure Resource Tagger - Frontend

React + TypeScript frontend for the Azure Resource Tagger application.

## Features

- 📊 **Dashboard**: Overview of resource tagging statistics and activity
- 📋 **Resource List**: Browse and manage Azure resources with classification status
- ✅ **Validation**: Review and approve LLM-generated classifications
- 📈 **Analytics**: Insights and metrics for resource tagging operations

## Tech Stack

- **React 18** with TypeScript
- **Vite** for fast development and building
- **TailwindCSS** for styling
- **React Router** for navigation
- **TanStack Query** for data fetching and caching
- **Axios** for API calls
- **Lucide React** for icons

## Prerequisites

- Node.js 18+ and npm/yarn/pnpm
- Backend API running on `http://localhost:8000`

## Installation

```bash
cd frontend
npm install
```

## Configuration

Create a `.env` file in the frontend directory:

```env
VITE_API_URL=http://localhost:8000
```

## Development

Start the development server:

```bash
npm run dev
```

The app will be available at `http://localhost:3000` with hot module replacement.

## Build

Build for production:

```bash
npm run build
```

Preview production build:

```bash
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── api/              # API client and resource endpoints
│   ├── components/       # Reusable React components
│   ├── pages/           # Page components (Dashboard, Resources, etc.)
│   ├── types/           # TypeScript type definitions
│   ├── App.tsx          # Main app component with routing
│   ├── main.tsx         # Application entry point
│   └── index.css        # Global styles and Tailwind directives
├── public/              # Static assets
├── index.html           # HTML template
├── vite.config.ts       # Vite configuration
├── tailwind.config.js   # Tailwind CSS configuration
└── package.json         # Dependencies and scripts
```

## API Integration

The frontend communicates with the FastAPI backend through the following endpoints:

- `GET /api/resources` - List all resources
- `POST /api/resources/discover` - Discover new resources
- `POST /api/resources/classify` - Classify resources using LLM
- `GET /api/classifications` - Get classifications with optional status filter
- `POST /api/classifications/approve` - Approve or reject classifications
- `POST /api/resources/apply-tags` - Apply tags to approved resources
- `GET /api/stats` - Get dashboard statistics

## Features

### Dashboard
- Real-time statistics on resource counts and classification status
- Distribution charts for workload taxonomy levels
- Recent activity timeline

### Resource List
- Searchable table of Azure resources
- Bulk selection and classification
- Status badges for classification pipeline stages
- Resource discovery integration

### Validation
- Review pending classifications with confidence scores
- Bulk approve/reject functionality
- Detailed classification reasoning and proposed tags
- One-click tag application

### Analytics
- Classification, approval, and application rate metrics
- Workload taxonomy distribution breakdowns
- Visual pipeline showing resource flow through stages

## Customization

### Styling

The project uses Tailwind CSS with a custom theme. Modify colors in `tailwind.config.js`:

```javascript
theme: {
  extend: {
    colors: {
      primary: {
        // Your brand colors
      }
    }
  }
}
```

### Dark Mode

Dark mode is supported via Tailwind's `dark:` variant. The system automatically detects user preferences.

## Troubleshooting

### API Connection Issues

If you see "Network Error" or API calls failing:

1. Ensure the backend is running on `http://localhost:8000`
2. Check CORS settings in backend configuration
3. Verify the `VITE_API_URL` in your `.env` file

### Build Errors

If you encounter build errors:

```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install

# Clear Vite cache
rm -rf .vite
```

## License

This project is part of the Azure Resource Tagger application.
