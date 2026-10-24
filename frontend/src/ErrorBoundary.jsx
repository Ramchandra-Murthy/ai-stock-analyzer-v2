import { Component } from "react";

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error) {
    console.error("EROS dashboard render error", error);
  }

  render() {
    if (this.state.hasError) {
      return (
        <main className="error-boundary" role="alert">
          <section className="panel">
            <p className="eyebrow">EROS · AI STOCK ANALYZER</p>
            <h1>Dashboard needs a refresh</h1>
            <p className="empty">
              The dashboard UI hit an unexpected rendering error. Your scanner
              backend and saved scan history are not changed by this screen.
            </p>
            <button className="secondary" onClick={() => window.location.reload()}>
              Reload dashboard
            </button>
          </section>
        </main>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
