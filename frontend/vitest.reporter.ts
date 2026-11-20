import { DefaultReporter } from "vitest/reporters";
import type { Vitest } from "vitest/node";

// Vitest's banner prints the absolute project root (which includes the OS username).
export default class NoRootPathReporter extends DefaultReporter {
  onInit(ctx: Vitest) {
    ctx.logger.printBanner = () => {
      ctx.logger.log(`\n RUN  v${ctx.version}\n`);
    };
    super.onInit(ctx);
  }
}
