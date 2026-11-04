// src/polyfills/domParser.ts
import { DOMParser } from "xmldom";

(global as any).DOMParser = DOMParser;
