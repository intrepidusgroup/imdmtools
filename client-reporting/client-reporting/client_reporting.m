//
//  client_reporting.m
//  client-reporting
//
//  Created by Black, Gavin S. on 12/20/13.
//  Copyright (c) 2013 Black, Gavin S. All rights reserved.
//

#import "client_reporting.h"

@implementation client_reporting

static NSString* mdmAddress = @"";
static BOOL doPause = NO;

+(void) setHostAddress: (NSString*) host {
   mdmAddress = [NSString stringWithFormat:@"https://%@/reporting/?type=", host];
}

+(void) setPause : (BOOL) toggle {
    doPause = toggle;
}

+(void) makeCall : (NSString*) urlStr {
    NSURL* url = [NSURL URLWithString:urlStr];
    [NSURLRequest requestWithURL:url];
    if(doPause) [NSThread sleepForTimeInterval:2.5];
}

+(void) reportJailbreak {
    [self makeCall:[NSString stringWithFormat:@"%@jailbreak", mdmAddress]];
}

+(void) reportDebugger {
    [self makeCall:[NSString stringWithFormat:@"%@debugger", mdmAddress]];
}

+(void) reportLocation : (CLLocationCoordinate2D*) coords {
    NSString *latitude = [NSString stringWithFormat:@"%f", coords->latitude];
    NSString *longitude = [NSString stringWithFormat:@"%f", coords->longitude];
    
    [self makeCall:[NSString stringWithFormat:@"%@location&lat=%@&lon=%@", mdmAddress, latitude, longitude]];
}




@end
