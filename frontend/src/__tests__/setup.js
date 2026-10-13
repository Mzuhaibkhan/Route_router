import "@testing-library/jest-dom";

if (typeof window !== "undefined") {
  if (!window.matchMedia) {
    window.matchMedia = (query) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => { },
      removeListener: () => { },
      addEventListener: () => { },
      removeEventListener: () => { },
      dispatchEvent: () => false,
    });
  }
  if (!window.scrollTo) {
    window.scrollTo = () => { };
  }
  if (!window.ResizeObserver) {
    window.ResizeObserver = class ResizeObserver {
      observe() { }
      unobserve() { }
      disconnect() { }
    };
  }

  // Mock Leaflet for testing
  window.L = {
    Icon: {
      Default: {
        prototype: {
          _getIconUrl: () => "",
        },
      },
    },
    DivIcon: class DivIcon {
      constructor(options) {
        this.options = options;
      }
    },
    LatLng: class LatLng {
      constructor(lat, lng) {
        this.lat = lat;
        this.lng = lng;
      }
    },
    LatLngBounds: class LatLngBounds {
      constructor(sw, ne) {
        this._southWest = sw;
        this._northEast = ne;
      }
    },
    Map: class Map {
      constructor() {
        this._container = document.createElement("div");
        this._zoom = 4;
        this._center = { lat: 37.5, lng: -95.5 };
      }
      setMaxBounds() { }
      setView() { }
      fitBounds() { }
      on() { }
      off() { }
      remove() { }
      getContainer() {
        return this._container;
      }
      getZoom() {
        return this._zoom;
      }
      getCenter() {
        return this._center;
      }
    },
    TileLayer: class TileLayer {
      constructor() { }
      addTo() { }
    },
    Polyline: class Polyline {
      constructor() { }
      addTo() { }
      setStyle() { }
      on() { }
      off() { }
    },
    CircleMarker: class CircleMarker {
      constructor() { }
      addTo() { }
      setStyle() { }
      on() { }
      off() { }
      getPopup() {
        return {
          setContent: () => { },
          open: () => { },
        };
      }
    },
    Popup: class Popup {
      constructor() { }
      setContent() { }
      open() { }
    },
    Tooltip: class Tooltip {
      constructor() { }
    },
    Control: {
      Zoom: class Zoom {
        constructor() { }
        addTo() { }
      },
    },
    DomUtil: {
      create: () => document.createElement("div"),
      addClass: () => { },
      removeClass: () => { },
    },
    DomEvent: {
      on: () => { },
      off: () => { },
      stopPropagation: () => { },
      preventDefault: () => { },
    },
    Browser: {
      touch: false,
      pointer: false,
    },
  };

  // Mock getComputedStyle for Leaflet
  window.getComputedStyle = (element) => {
    return {
      getPropertyValue: () => "",
      width: "800px",
      height: "600px",
    };
  };

  // Mock requestAnimationFrame
  window.requestAnimationFrame = (callback) => setTimeout(callback, 16);
  window.cancelAnimationFrame = (id) => clearTimeout(id);
}
