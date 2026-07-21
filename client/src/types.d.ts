declare module 'plotly.js-dist-min' {
  interface PlotData {
    [key: string]: any;
  }
  interface PlotLayout {
    [key: string]: any;
  }
  interface PlotConfig {
    [key: string]: any;
  }
  function newPlot(
    root: HTMLElement,
    data: PlotData[],
    layout?: PlotLayout,
    config?: PlotConfig
  ): Promise<PlotlyHTMLElement>;
  function purge(root: HTMLElement): void;
  function downloadImage(
    root: HTMLElement,
    opts: {
      format?: string;
      width?: number;
      height?: number;
      filename?: string;
    }
  ): Promise<void>;
  interface PlotlyHTMLElement extends HTMLElement {}
  export { newPlot, purge, downloadImage };
  export default { newPlot, purge, downloadImage };
}

declare module 'rehype-sanitize' {
  import type { Plugin } from 'unified';
  const rehypeSanitize: Plugin;
  export default rehypeSanitize;
}
