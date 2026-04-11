const LoadingSpinner = () => {
  return (
    <div className="flex justify-start">
      <div className="flex items-center gap-3 bg-card px-4 py-3 rounded-md">
        <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin-slow" />
        <span className="text-xs text-muted-foreground font-mono">Querying database...</span>
      </div>
    </div>
  );
};

export default LoadingSpinner;
