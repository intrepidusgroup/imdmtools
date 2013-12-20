//
//  client_reporting.h
//  client-reporting
//
//  Created by Black, Gavin S. on 12/20/13.
//  Copyright (c) 2013 Black, Gavin S. All rights reserved.
//

#import <Foundation/Foundation.h>
#import <CoreLocation/CoreLocation.h>


@interface client_reporting : NSObject
+(void) setHostAddress: (NSString*) host;
+(void) setPause : (BOOL) toggle;


+(void) reportJailbreak;
+(void) reportDebugger;
+(void) reportLocation : (CLLocationCoordinate2D*) coords;


@end
