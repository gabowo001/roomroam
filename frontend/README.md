# RoomRoam TypeScript Frontend

This is the TypeScript version of the RoomRoam chat application.

## Features

- Real-time group chat functionality
- User identification with random usernames
- Connection status indicator
- Responsive design for mobile and desktop
- Message history retrieval
- Modern UI with purple/violet color scheme

## Technologies Used

- **React**: JavaScript library for building user interfaces
- **TypeScript**: Typed superset of JavaScript
- **Vite**: Fast build tool and development server
- **Axios**: HTTP client for API requests
- **CSS**: Custom styling

## Dependencies

- `react`, `react-dom`: Core React libraries
- `axios`: HTTP client for API communication
- `web-vitals`: Web performance metrics
- Testing libraries: `@testing-library/jest-dom`, `@testing-library/react`, `@testing-library/user-event`

## Development

1. Install dependencies:
   ```
   npm install
   ```

2. Start the development server:
   ```
   npm run dev
   ```

3. Build for production:
   ```
   npm run build
   ```

## Project Structure

```
src/
├── App.tsx         # Main chat application component
├── App.css         # Styling for the chat application
├── index.tsx       # Entry point
└── index.css       # Global styles
```

## API Communication

The frontend communicates with the backend via `/api` endpoints, which are proxied to the backend server running on port 5000.

## Migration from JavaScript

This project was migrated from a JavaScript React application to TypeScript. Key changes include:

1. Conversion of `.js` files to `.tsx` files
2. Addition of type annotations for all variables and function parameters
3. Creation of interfaces for API response data
4. Migration from Create React App to Vite
5. Update of build configurations