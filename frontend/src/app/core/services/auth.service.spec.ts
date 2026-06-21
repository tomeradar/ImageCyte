import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Router } from '@angular/router';
import { AuthService } from './auth.service';

describe('AuthService', () => {
  let service: AuthService;
  let httpMock: HttpTestingController;
  let routerMock: any;

  beforeEach(() => {
    routerMock = {
      navigate: vi.fn()
    };

    TestBed.configureTestingModule({
      providers: [
        AuthService,
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: Router, useValue: routerMock }
      ]
    });
    service = TestBed.inject(AuthService);
    httpMock = TestBed.inject(HttpTestingController);
    localStorage.clear();
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should return false for isLoggedIn$ when token is missing', () => {
    let loggedIn = true;
    service.isLoggedIn$.subscribe(val => loggedIn = val);
    expect(loggedIn).toBe(false);
  });

  it('should store tokens in localStorage on login', () => {
    const mockResponse = {
      access_token: 'mock-access-token',
      refresh_token: 'mock-refresh-token'
    };

    service.login('test.user', 'password').subscribe(res => {
      expect(res).toEqual(mockResponse);
      let loggedIn = false;
      service.isLoggedIn$.subscribe(val => loggedIn = val);
      expect(loggedIn).toBe(true);
      expect(service.getAccessToken()).toBe('mock-access-token');
    });

    const req = httpMock.expectOne('http://localhost:8000/api/proxy/login');
    expect(req.request.method).toBe('POST');
    req.flush(mockResponse);
  });

  it('should clear tokens on logout', () => {
    // Log in first to populate state
    service.login('test.user', 'password').subscribe();
    const req = httpMock.expectOne('http://localhost:8000/api/proxy/login');
    req.flush({ access_token: 'token', refresh_token: 'refresh' });

    let loggedIn = false;
    service.isLoggedIn$.subscribe(val => loggedIn = val);
    expect(loggedIn).toBe(true);
    
    // Log out and assert state is cleared
    service.logout();
    
    service.isLoggedIn$.subscribe(val => loggedIn = val);
    expect(loggedIn).toBe(false);
    expect(service.getAccessToken()).toBeNull();
    expect(routerMock.navigate).toHaveBeenCalledWith(['/login']);
  });
});
