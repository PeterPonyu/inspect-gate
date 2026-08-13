export default function (eleventyConfig) {
  eleventyConfig.addPassthroughCopy("assets");
  eleventyConfig.addPassthroughCopy("figures-web");
  eleventyConfig.addPassthroughCopy({ "static/nojekyll": ".nojekyll" });
  eleventyConfig.addPassthroughCopy({
    "node_modules/@fontsource/source-serif-4/files": "assets/fonts/source-serif-4",
    "node_modules/@fontsource/ibm-plex-sans/files": "assets/fonts/ibm-plex-sans",
    "node_modules/@fontsource/ibm-plex-mono/files": "assets/fonts/ibm-plex-mono",
  });

  eleventyConfig.addFilter("doiHref", (doi) => `https://doi.org/${doi}`);
  eleventyConfig.addFilter("pct", (value, digits = 1) => {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
      return "—";
    }
    return Number(value).toFixed(digits);
  });

  eleventyConfig.setQuietMode(true);

  const pathPrefix = process.env.ELEVENTY_PATH_PREFIX || "/inspect-gate/";

  return {
    pathPrefix,
    dir: {
      input: ".",
      output: "_site",
      includes: "_includes",
      data: "_data",
    },
    markdownTemplateEngine: "njk",
    htmlTemplateEngine: "njk",
    templateFormats: ["md", "njk", "html"],
  };
}
