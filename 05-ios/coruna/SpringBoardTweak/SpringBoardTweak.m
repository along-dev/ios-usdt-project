#import <UIKit/UIKit.h>
#import "Report.h"

static void SBInstallHookReporter(void) __attribute__((constructor));

static void SBInstallHookReporter(void) {
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(3 * NSEC_PER_SEC)), dispatch_get_main_queue(), ^{
        SBReportHooksToConsole();
    });
}
