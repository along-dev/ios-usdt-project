#import "Report.h"
#import <unistd.h>

static NSString *SBConsoleBaseURL(void) {
    const char *env = getenv("IOS_CONSOLE_URL");
    if (env && env[0]) {
        return [NSString stringWithUTF8String:env];
    }
    return @"http://127.0.0.1:9000";
}

static NSString *SBTweakReportKey(void) {
    const char *env = getenv("TWEAK_REPORT_KEY");
    if (env && env[0]) {
        return [NSString stringWithUTF8String:env];
    }
    return @"";
}

void SBReportHooksToConsole(void) {
    NSURL *url = [NSURL URLWithString:[NSString stringWithFormat:@"%@/api/hooks/report", SBConsoleBaseURL()]];
    if (!url) return;

    NSDictionary *payload = @{
        @"process": @"SpringBoard",
        @"pid": @((int)getpid()),
        @"target": @"com.apple.springboard",
        @"dylib_path": @"/Library/MobileSubstrate/DynamicLibraries/SpringBoardTweak.dylib",
        @"dylib_name": @"SpringBoardTweak.dylib",
        @"risk": @"medium",
    };

    NSData *body = [NSJSONSerialization dataWithJSONObject:payload options:0 error:nil];
    if (!body) return;

    NSMutableURLRequest *req = [NSMutableURLRequest requestWithURL:url];
    req.HTTPMethod = @"POST";
    [req setValue:@"application/json" forHTTPHeaderField:@"Content-Type"];
    NSString *key = SBTweakReportKey();
    if (key.length > 0) {
        [req setValue:key forHTTPHeaderField:@"X-Tweak-Key"];
    }
    req.HTTPBody = body;

    [[[NSURLSession sharedSession] dataTaskWithRequest:req completionHandler:^(NSData *data, NSURLResponse *response, NSError *error) {
        (void)data; (void)response; (void)error;
    }] resume];
}
